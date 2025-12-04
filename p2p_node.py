from __future__ import annotations
import json
import threading
import uuid
import time  # <- slow-join ve log için

from typing import Any, Dict, List, Optional, Sequence, Tuple
import zmq

from move_op_impl import Move, ThreadSafeState, pretty_tree
from my_marshal import to_jsonable


class LamportClock:
    """Very small Lamport logical clock"""

    def __init__(self, initial: int = 0) -> None:
        self._lock = threading.Lock()
        self._t = int(initial)

    def tick(self) -> int:
        """bump local time when we create a new local operation"""
        with self._lock:
            self._t += 1
            return self._t

    def update_on_receive(self, received_ts: int) -> int:
        """merge time when we receive a remote operation"""
        with self._lock:
            self._t = max(self._t, int(received_ts)) + 1
            return self._t


class PubSubMoveNode:
    """
    - PUB: we broadcast operations we perform locally
    - SUB: we listen to operations from peers and apply them
    - REP: a small query endpoint (snapshot / pretty) for debugging

    - We keep a 'seen message id' set to avoid re-applying duplicates
    - We do NOT add any extra field to Move; msg_id lives only in the wire payload
    """

    def __init__(
        self,
        pub_bind: str,
        rep_bind: str,
        peer_pub_endpoints: Optional[Sequence[str]] = None,
        default_topics: Optional[Sequence[str]] = None,
        initial_tree: Optional[Sequence[Tuple[Any, Any, Any]]] = None,
    ) -> None:
        # CRDT state (thread-safe)
        self.state = ThreadSafeState(set(initial_tree) if initial_tree else None)
        self.clock = LamportClock()

        # Idempotency at the message layer, skip already processed messages
        self._seen_msgs: set[str] = set()

        # ZeroMQ context and sockets
        self.ctx = zmq.Context.instance()

        # This node's publisher
        self.pub = self.ctx.socket(zmq.PUB)
        self.pub.bind(pub_bind)

        # subscriber to peers publishers
        self.sub = self.ctx.socket(zmq.SUB)
        if default_topics is None:
            default_topics = ("apply", "apply_batch", "undo", "redo")
        for t in default_topics:
            self.sub.setsockopt_string(zmq.SUBSCRIBE, t)
        for ep in (peer_pub_endpoints or []):
            self.sub.connect(ep)

        # ---- Slow-join fix: SUB bağlandıktan sonra kısa gecikme
        # ilk publish'lerin kaybolmaması için
        time.sleep(0.3)

        # simple REP server for queries
        self.rep = self.ctx.socket(zmq.REP)
        self.rep.bind(rep_bind)

        # handlers map for SUB topics
        self._sub_handlers: Dict[str, List] = {t: [] for t in default_topics}
        self._wire_default_handlers()

        # background threads for SUB/REP loops
        self._running = True
        self._sub_thread = threading.Thread(target=self._subscribe_loop, daemon=True)
        self._rep_thread = threading.Thread(target=self._rep_loop, daemon=True)
        self._sub_thread.start()
        self._rep_thread.start()

    # ---------- background loops ----------

    def _subscribe_loop(self) -> None:
        """Receive peer messages and dispatch to handlers"""
        while self._running:
            try:
                topic_b, payload_b = self.sub.recv_multipart(flags=0)
                topic = topic_b.decode("utf-8")
                data = json.loads(payload_b.decode("utf-8"))

                # merge Lamport time using the largest move_time in this message
                msg_time = data.get("move", {}).get("move_time")
                if msg_time is None and "moves" in data:
                    try:
                        msg_time = max(int(m.get("move_time", 0)) for m in data["moves"])
                    except ValueError:
                        msg_time = None
                if msg_time is not None:
                    self.clock.update_on_receive(int(msg_time))

                # deliver to registered handlers for this topic
                for h in self._sub_handlers.get(topic, []):
                    try:
                        h(topic, data)
                    except Exception:
                        # swallow handler errors to keep the loop alive
                        pass
            except zmq.ZMQError:
                break

    def _rep_loop(self) -> None:
        """Serve small debug queries (snapshot / pretty)"""
        while self._running:
            try:
                req = self.rep.recv_json()
                cmd = req.get("cmd")
                if cmd == "snapshot":
                    tree = self.state.tree()
                    self.rep.send_json({"ok": True, "tree": list(tree)})
                elif cmd == "pretty":
                    tree = self.state.tree()
                    self.rep.send_json({"ok": True, "pretty": pretty_tree(tree)})
                else:
                    self.rep.send_json({"ok": False, "error": f"unknown cmd: {cmd}"})
            except zmq.ZMQError:
                break
            except Exception as e:
                # on unexpected error try to reply with a clean error payload
                try:
                    self.rep.send_json({"ok": False, "error": str(e)})
                except Exception:
                    pass

    # ---------- public operations (local apply + publish) ----------

    def apply(self, move_parent: Any, move_meta: Any, move_child: Any, move_time: Optional[int] = None) -> None:
        """
        Apply a single move locally and publish it to peers.

        - move_time: if None, assigned from the local Lamport clock.
        - msg_id: generated per message; carried only on the wire to prevent duplicates.
        """
        if move_time is None:
            move_time = self.clock.tick()

        msg_id = uuid.uuid4().hex

        self.state.apply(Move(move_time, move_parent, move_meta, move_child))

        # broadcast the op to peers (msg_id is in the payload only)
        payload = {
            "move": {
                "move_time": move_time,
                "move_parent": move_parent,
                "move_meta": move_meta,
                "move_child": move_child,
                "msg_id": msg_id,
            }
        }
        self._send("apply", payload)

    def apply_batch(self, moves: Sequence[Tuple[Any, Any, Any]]) -> None:
        """
        Apply a batch of moves locally and publish them together

        Each entry is (parent, meta, child)
        Every move gets its own timestamp (tick) and msg_id
        """
        batch = []
        for (p, m, c) in moves:
            ts = self.clock.tick()
            msg_id = uuid.uuid4().hex

            # Local apply
            self.state.apply(Move(ts, p, m, c))

            # Collect payload for broadcast
            batch.append({
                "move_time": ts,
                "move_parent": p,
                "move_meta": m,
                "move_child": c,
                "msg_id": msg_id,
            })

        self._send("apply_batch", {"moves": batch})

    def undo(self, n: int = 1) -> None:
        """Undo n operations locally and publish the request."""
        self.state.undo(int(n))
        self._send("undo", {"n": int(n)})

    def redo(self, n: int = 1) -> None:
        """Redo n operations locally and publish the request."""
        self.state.redo(int(n))
        self._send("redo", {"n": int(n)})

    # ---------- convenience helpers ----------

    def pretty(self) -> str:
        """Return a pretty-printed view of the current tree."""
        return pretty_tree(self.state.tree())

    def print_pretty(self) -> None:
        """Print the pretty-printed view (quick manual debug)."""
        print(self.pretty())

    def on(self, topic: str, handler) -> None:
        """Register a callback for a SUB topic (apply / apply_batch / undo / redo)."""
        self._sub_handlers.setdefault(topic, []).append(handler)

    # ---------- default SUB handlers ----------

    def _wire_default_handlers(self) -> None:
        """Default handlers that apply incoming messages to local state."""

        def _h_apply(_topic, data):
            mv = data["move"]
            msg_id = mv.get("msg_id")

            # idempotency
            if msg_id and msg_id in self._seen_msgs:
                return
            if msg_id:
                self._seen_msgs.add(msg_id)

            self.clock.update_on_receive(int(mv.get("move_time", 0)))
            self.state.apply(Move(mv["move_time"], mv["move_parent"], mv["move_meta"], mv["move_child"]))

            # ---- otomatik görünürlük: geleni ve güncel ağacı yazdır
            print("\n[RX] apply:", mv)
            print(self.pretty())

        def _h_apply_batch(_topic, data):
            for mv in data.get("moves", []):
                msg_id = mv.get("msg_id")
                if msg_id and msg_id in self._seen_msgs:
                    continue
                if msg_id:
                    self._seen_msgs.add(msg_id)

                self.clock.update_on_receive(int(mv.get("move_time", 0)))
                self.state.apply(Move(mv["move_time"], mv["move_parent"], mv["move_meta"], mv["move_child"]))

            print("\n[RX] apply_batch:", data.get("moves", []))
            print(self.pretty())

        def _h_undo(_topic, data):
            self.state.undo(int(data.get("n", 1)))
            print("\n[RX] undo:", data)
            print(self.pretty())

        def _h_redo(_topic, data):
            self.state.redo(int(data.get("n", 1)))
            print("\n[RX] redo:", data)
            print(self.pretty())

        self.on("apply", _h_apply)
        self.on("apply_batch", _h_apply_batch)
        self.on("undo", _h_undo)
        self.on("redo", _h_redo)

    # ---------- publishing helper ----------

    def _send(self, topic: str, payload: Dict[str, Any]) -> None:
        """Publish a message to peers (topic + JSON payload)."""
        # yayın öncesi görünür log
        try:
            print(f"\n[TX] {topic}: {payload}")
        except Exception:
            pass

        try:
            self.pub.send_multipart([topic.encode("utf-8"), json.dumps(to_jsonable(payload)).encode("utf-8")])
        except Exception:
            # sessizce geç; ağ kesilirse node çalışmaya devam etsin
            pass

    # ---------- optional: query another node's REP endpoint ----------

    def query_peer(self, peer_rep: str, cmd: str) -> Dict[str, Any]:
        req = self.ctx.socket(zmq.REQ)
        try:
            req.connect(peer_rep)
            req.send_json({"cmd": cmd})
            return req.recv_json()
        finally:
            try:
                req.close(0)
            except Exception:
                pass

    # ---------- shutdown ----------

    def close(self) -> None:
        """Close sockets and stop background threads"""
        self._running = False
        try:
            self.sub.close(0)
            self.pub.close(0)
            self.rep.close(0)
        except Exception:
            pass
