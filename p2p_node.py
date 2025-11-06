from __future__ import annotations
import json
import threading
from typing import Any, Dict, List, Optional, Sequence, Tuple

import zmq

from move_op_impl import Move, ThreadSafeState, pretty_tree
from my_marshal import to_jsonable


class LamportClock:
    """Minimal Lamport logical clock.

    - tick(): increments and returns the local time
    - update_on_receive(ts): merges with received timestamp and returns new time
    """

    def __init__(self, initial: int = 0) -> None:
        self._lock = threading.Lock()
        self._t = int(initial)

    def tick(self) -> int:
        with self._lock:
            self._t += 1
            return self._t

    def update_on_receive(self, received_ts: int) -> int:
        with self._lock:
            self._t = max(self._t, int(received_ts)) + 1
            return self._t


class PubSubMoveNode:
    """
    P2P wrapper for CRDT move operations using ZeroMQ PUB/SUB for ops and REP for queries.

    - Each node:
      - binds a PUB socket to broadcast operations (apply/apply_batch/undo/redo)
      - connects a SUB socket to peer PUB endpoints and applies received ops
      - binds a REP socket to answer queries (snapshot, pretty)

    - Op-based dissemination: send only operations, not full state.
    - Eventual consistency via Lamport timestamps (merged on receive).
    """

    def __init__(
        self,
        pub_bind: str,
        rep_bind: str,
        peer_pub_endpoints: Optional[Sequence[str]] = None,
        default_topics: Optional[Sequence[str]] = None,
        initial_tree: Optional[Sequence[Tuple[Any, Any, Any]]] = None,
    ) -> None:
        # State
        self.state = ThreadSafeState(set(initial_tree) if initial_tree else None)
        self.clock = LamportClock()

        # ZMQ
        self.ctx = zmq.Context.instance()

        # PUB (bind) - this node's broadcast endpoint
        self.pub = self.ctx.socket(zmq.PUB)
        self.pub.bind(pub_bind)

        # SUB (connect) - connect to peers' PUBs
        self.sub = self.ctx.socket(zmq.SUB)
        if default_topics is None:
            default_topics = ("apply", "apply_batch", "undo", "redo")
        for t in default_topics:
            self.sub.setsockopt_string(zmq.SUBSCRIBE, t)
        peer_pub_endpoints = peer_pub_endpoints or []
        for ep in peer_pub_endpoints:
            self.sub.connect(ep)

        # REP (bind) - serve queries
        self.rep = self.ctx.socket(zmq.REP)
        self.rep.bind(rep_bind)

        # Handlers for SUB topics
        self._sub_handlers: Dict[str, List] = {t: [] for t in default_topics}
        self._wire_default_handlers()

        # Threads
        self._running = True
        self._sub_thread = threading.Thread(target=self._subscribe_loop, daemon=True)
        self._rep_thread = threading.Thread(target=self._rep_loop, daemon=True)
        self._sub_thread.start()
        self._rep_thread.start()

    # --------------- Networking loops ---------------
    def _subscribe_loop(self) -> None:
        while self._running:
            try:
                topic_b, payload_b = self.sub.recv_multipart(flags=0)
                topic = topic_b.decode("utf-8")
                data = json.loads(payload_b.decode("utf-8"))

                # Lamport merge (use op timestamp(s) if present)
                msg_time = data.get("move", {}).get("move_time")
                if msg_time is None and "moves" in data:
                    try:
                        msg_time = max(int(m.get("move_time", 0)) for m in data["moves"])  # type: ignore[arg-type]
                    except ValueError:
                        msg_time = None
                if msg_time is not None:
                    self.clock.update_on_receive(int(msg_time))

                for h in self._sub_handlers.get(topic, []):
                    try:
                        h(topic, data)
                    except Exception:
                        pass
            except zmq.ZMQError:
                break

    def _rep_loop(self) -> None:
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
                try:
                    self.rep.send_json({"ok": False, "error": str(e)})
                except Exception:
                    pass

    # --------------- Public API (fire-and-forget ops) ---------------
    def apply(self, move_parent: Any, move_meta: Any, move_child: Any, move_time: Optional[int] = None) -> None:
        if move_time is None:
            move_time = self.clock.tick()
        # Apply locally immediately
        self.state.apply(Move(move_time, move_parent, move_meta, move_child))
        # Broadcast op
        self._send("apply", {"move": {
            "move_time": move_time,
            "move_parent": move_parent,
            "move_meta": move_meta,
            "move_child": move_child,
        }})

    def apply_batch(self, moves: Sequence[Tuple[Any, Any, Any]]) -> None:
        batch = []
        for (p, m, c) in moves:
            ts = self.clock.tick()
            # Apply locally
            self.state.apply(Move(ts, p, m, c))
            batch.append({"move_time": ts, "move_parent": p, "move_meta": m, "move_child": c})
        # Broadcast
        self._send("apply_batch", {"moves": batch})

    def undo(self, n: int = 1) -> None:
        self.state.undo(int(n))
        self._send("undo", {"n": int(n)})

    def redo(self, n: int = 1) -> None:
        self.state.redo(int(n))
        self._send("redo", {"n": int(n)})

    # --------------- SUB handlers and send helper ---------------
    def pretty(self) -> str:
        """Return pretty-printed current tree."""
        return pretty_tree(self.state.tree())

    def print_pretty(self) -> None:
        """Print pretty-printed current tree to stdout."""
        print(self.pretty())

    def on(self, topic: str, handler) -> None:
        self._sub_handlers.setdefault(topic, []).append(handler)

    def _wire_default_handlers(self) -> None:
        def _h_apply(_topic, data):
            mv = data["move"]
            self.clock.update_on_receive(int(mv.get("move_time", 0)))
            self.state.apply(Move(mv["move_time"], mv["move_parent"], mv["move_meta"], mv["move_child"]))

        def _h_apply_batch(_topic, data):
            for mv in data.get("moves", []):
                self.clock.update_on_receive(int(mv.get("move_time", 0)))
                self.state.apply(Move(mv["move_time"], mv["move_parent"], mv["move_meta"], mv["move_child"]))

        def _h_undo(_topic, data):
            self.state.undo(int(data.get("n", 1)))

        def _h_redo(_topic, data):
            self.state.redo(int(data.get("n", 1)))

        self.on("apply", _h_apply)
        self.on("apply_batch", _h_apply_batch)
        self.on("undo", _h_undo)
        self.on("redo", _h_redo)

    def _send(self, topic: str, payload: Dict[str, Any]) -> None:
        try:
            self.pub.send_multipart([topic.encode("utf-8"), json.dumps(to_jsonable(payload)).encode("utf-8")])
        except Exception:
            pass

    # --------------- Helper: query another peer's REP ---------------
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

    # --------------- Cleanup ---------------
    def close(self) -> None:
        self._running = False
        try:
            self.sub.close(0)
            self.pub.close(0)
            self.rep.close(0)
        except Exception:
            pass


