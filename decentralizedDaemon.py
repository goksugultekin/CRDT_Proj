from __future__ import annotations
import json
from typing import Any, Dict, List, Optional, Set, Tuple
import threading
import zmq

from move_op_impl import Move, ThreadSafeState, pretty_tree
from my_marshal import to_jsonable, move_to_dict, logmove_to_dict, tree_to_list, LamportClock


class decentralizedDaemon:
    def __init__(
        self,
        rep_bind: str = "tcp://*:5555",
        pub_bind: str = "tcp://*:5556",
        initial_tree: Optional[Set[Tuple[Any, Any, Any]]] = None,
    ):
        self.state = ThreadSafeState(initial_tree)
        self.clock = LamportClock()

        self.ctx = zmq.Context.instance()

        self.rep = self.ctx.socket(zmq.REP)
        self.rep.bind(rep_bind)

        self.pub = self.ctx.socket(zmq.PUB)
        self.pub.bind(pub_bind)

        self._stop = threading.Event()

    # ---- helpers ----
    def _reply(self, **payload):
        self.rep.send_json(to_jsonable({"ok": True, **payload}))

    def _reply_error(self, msg: str):
        self.rep.send_json({"ok": False, "error": msg})

    def _broadcast(self, topic: str, payload: Dict[str, Any]):
        self.pub.send_multipart([
            topic.encode("utf-8"),
            json.dumps(to_jsonable(payload)).encode("utf-8")
        ])

    # ---- main loop ----
    def serve_forever(self):
        while not self._stop.is_set():
            try:
                req = self.rep.recv_json(flags=0)
            except zmq.ZMQError:
                break

            cmd = req.get("cmd")
            try:
                if cmd == "apply":
                    move_dict = req["move"]
                    client_ts = move_dict.get("move_time")
                    if client_ts is not None:
                        self.clock.update_on_receive(int(client_ts))
                        ts = self.clock.now()
                    else:
                        ts = self.clock.tick()

                    mv = Move(ts, move_dict["move_parent"], move_dict["move_meta"], move_dict["move_child"])
                    self.state.apply(mv)
                    log, tree = self.state.snapshot()

                    self._reply(
                        log=[logmove_to_dict(x) for x in log],
                        tree=tree_to_list(tree),
                        applied=move_to_dict(mv),
                    )
                    self._broadcast("applied", {"move": move_to_dict(mv), "tree": tree_to_list(tree)})

                elif cmd == "apply_batch":
                    moves: List[Dict[str, Any]] = req["moves"]
                    applied: List[Dict[str, Any]] = []
                    for md in moves:
                        client_ts = md.get("move_time")
                        if client_ts is not None:
                            self.clock.update_on_receive(int(client_ts))
                            ts = self.clock.now()
                        else:
                            ts = self.clock.tick()

                        mv = Move(ts, md["move_parent"], md["move_meta"], md["move_child"])
                        self.state.apply(mv)
                        applied.append(move_to_dict(mv))

                    log, tree = self.state.snapshot()
                    self._reply(
                        log=[logmove_to_dict(x) for x in log],
                        tree=tree_to_list(tree),
                        applied=applied,
                    )
                    self._broadcast("applied_batch", {"moves": applied, "tree": tree_to_list(tree)})

                elif cmd == "undo":
                    n = int(req.get("n", 1))
                    self.clock.tick()
                    self.state.undo(n)
                    log, tree = self.state.snapshot()
                    self._reply(log=[logmove_to_dict(x) for x in log], tree=tree_to_list(tree))
                    self._broadcast("undone", {"n": n, "tree": tree_to_list(tree)})

                elif cmd == "redo":
                    n = int(req.get("n", 1))
                    self.clock.tick()
                    self.state.redo(n)
                    log, tree = self.state.snapshot()
                    self._reply(log=[logmove_to_dict(x) for x in log], tree=tree_to_list(tree))
                    self._broadcast("redone", {"n": n, "tree": tree_to_list(tree)})

                elif cmd == "snapshot":
                    log, tree = self.state.snapshot()
                    self._reply(log=[logmove_to_dict(x) for x in log], tree=tree_to_list(tree))

                elif cmd == "pretty":
                    tree = self.state.tree()
                    self._reply(pretty=pretty_tree(tree))

                else:
                    self._reply_error(f"unknown cmd: {cmd}")

            except Exception as e:
                self._reply_error(str(e))

    def stop(self):
        self._stop.set()
        try:
            self.rep.close(0)
            self.pub.close(0)
        finally:
            self.ctx.term()
