# ZeroMQ-based CRDT server for distributed operations

from __future__ import annotations
import json
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import zmq
from move_op_impl import Move, ThreadSafeState, pretty_tree
from my_marshal import move_from_dict, logmove_to_dict, tree_to_list

class CRDTServer:
    def __init__(self, rep_port: int = 5555, pub_port: int = 5556):
        print("Starting CRDT Server...")
        self.ctx = zmq.Context.instance()

        self.rep = self.ctx.socket(zmq.REP)
        self.rep.bind(f"tcp://*:{rep_port}")
        print(f"  REP socket: tcp://*:{rep_port}")

        self.pub = self.ctx.socket(zmq.PUB)
        self.pub.bind(f"tcp://*:{pub_port}")
        print(f"  PUB socket: tcp://*:{pub_port}")

        initial_tree = {("root", "", "A"), ("root", "", "B")}
        self.state = ThreadSafeState(initial_tree)
        print(f"  Initial tree: {len(initial_tree)} nodes")

        self._running = True
        self._server_thread = threading.Thread(target=self._handle_requests, daemon=True)
        self._server_thread.start()
        print("CRDT Server started successfully!")

    def _handle_requests(self):
        print("Request handler started...")
        while self._running:
            try:
                request = self.rep.recv_json()
                response = self._process_request(request)
                self.rep.send_json(response)
            except zmq.ZMQError as e:
                if self._running:
                    print(f"  ZMQ error: {e}")
                break
            except Exception as e:
                print(f"  Error: {e}")
                try:
                    self.rep.send_json({"ok": False, "error": str(e)})
                except:
                    pass

    def _process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        cmd = request.get("cmd")
        try:
            if cmd == "apply":
                return self._handle_apply(request)
            elif cmd == "apply_batch":
                return self._handle_apply_batch(request)
            elif cmd == "undo":
                return self._handle_undo(request)
            elif cmd == "redo":
                return self._handle_redo(request)
            elif cmd == "snapshot":
                return self._handle_snapshot(request)
            elif cmd == "pretty":
                return self._handle_pretty(request)
            else:
                return {"ok": False, "error": f"Unknown command: {cmd}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _handle_apply(self, request: Dict[str, Any]) -> Dict[str, Any]:
        move_data = request["move"]
        move = move_from_dict(move_data)
        self.state.apply(move)

        log = self.state.log()
        tree = self.state.tree()
        self._broadcast("applied", {
            "move": move_data,
            "log": [logmove_to_dict(l) for l in log],
            "tree": tree_to_list(tree)
        })
        return {"ok": True, "log": [logmove_to_dict(l) for l in log], "tree": tree_to_list(tree)}

    def _handle_apply_batch(self, request: Dict[str, Any]) -> Dict[str, Any]:
        moves_data = request["moves"]
        moves = [move_from_dict(m) for m in moves_data]
        for move in moves:
            self.state.apply(move)

        log = self.state.log()
        tree = self.state.tree()
        self._broadcast("applied_batch", {
            "moves": moves_data,
            "log": [logmove_to_dict(l) for l in log],
            "tree": tree_to_list(tree)
        })
        return {"ok": True, "log": [logmove_to_dict(l) for l in log], "tree": tree_to_list(tree)}

    def _handle_undo(self, request: Dict[str, Any]) -> Dict[str, Any]:
        n = int(request.get("n", 1))
        self.state.undo(n)
        log = self.state.log()
        tree = self.state.tree()
        self._broadcast("undone", {"n": n, "log": [logmove_to_dict(l) for l in log], "tree": tree_to_list(tree)})
        return {"ok": True, "log": [logmove_to_dict(l) for l in log], "tree": tree_to_list(tree)}

    def _handle_redo(self, request: Dict[str, Any]) -> Dict[str, Any]:
        n = int(request.get("n", 1))
        self.state.redo(n)
        log = self.state.log()
        tree = self.state.tree()
        self._broadcast("redone", {"n": n, "log": [logmove_to_dict(l) for l in log], "tree": tree_to_list(tree)})
        return {"ok": True, "log": [logmove_to_dict(l) for l in log], "tree": tree_to_list(tree)}

    def _handle_snapshot(self, request: Dict[str, Any]) -> Dict[str, Any]:
        tree = self.state.tree()
        return {"ok": True, "tree": tree_to_list(tree)}

    def _handle_pretty(self, request: Dict[str, Any]) -> Dict[str, Any]:
        pretty_str = pretty_tree(self.state.tree())
        return {"ok": True, "pretty": pretty_str}

    def _broadcast(self, topic: str, data: Dict[str, Any]):
        try:
            message = json.dumps(data)
            self.pub.send_multipart([topic.encode("utf-8"), message.encode("utf-8")])
        except Exception:
            pass

    def close(self):
        self._running = False
        try:
            self.rep.close(0)
            self.pub.close(0)
        except Exception:
            pass

def logmove_to_dict(lm) -> Dict[str, Any]:
    return {
        "log_time": lm.log_time,
        "old_parent": lm.old_parent,
        "new_parent": lm.new_parent,
        "log_meta": lm.log_meta,
        "log_child": lm.log_child,
    }
