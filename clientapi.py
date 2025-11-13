# Client API methods for CRDT operations

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional, Tuple  # ← Tuple eklendi
from my_marshal import to_jsonable

class ClientAPI:
    """Client API methods for CRDT operations"""

    def __init__(self, client):
        self.client = client
        self.clock = client.clock

    def apply(self, move_parent: Any, move_meta: Any, move_child: Any, move_time: Optional[int] = None):
        """Apply a single move operation"""
        if move_time is None:
            move_time = self.clock.tick()  # propose a timestamp
        msg = {"cmd": "apply", "move": {
            "move_time": move_time,
            "move_parent": move_parent,
            "move_meta": move_meta,
            "move_child": move_child
        }}
        resp = self.client._send(msg)
        log = resp.get("log", [])
        if log:
            self.clock.update_on_receive(max(int(l["log_time"]) for l in log))
        return resp

    def apply_batch(self, moves: List[Tuple[Any, Any, Any]]):
        """
        Apply multiple move operations in batch
        moves: list of (parent, meta, child). move_time is assigned from local Lamport.
        """
        batch = []
        for (p, m, c) in moves:
            batch.append({
                "move_time": self.clock.tick(),
                "move_parent": p,
                "move_meta": m,
                "move_child": c
            })
        resp = self.client._send({"cmd": "apply_batch", "moves": batch})
        log = resp.get("log", [])
        if log:
            self.clock.update_on_receive(max(int(l["log_time"]) for l in log))
        return resp

    def undo(self, n: int = 1):
        """Undo n operations"""
        resp = self.client._send({"cmd": "undo", "n": n})
        log = resp.get("log", [])
        if log:
            self.clock.update_on_receive(max(int(l["log_time"]) for l in log))
        return resp

    def redo(self, n: int = 1):
        """Redo n operations"""
        resp = self.client._send({"cmd": "redo", "n": n})
        log = resp.get("log", [])
        if log:
            self.clock.update_on_receive(max(int(l["log_time"]) for l in log))
        return resp

    def snapshot(self):
        """Get current tree snapshot"""
        return self.client._send({"cmd": "snapshot"})

    def pretty(self) -> str:
        """Get pretty-printed tree representation"""
        return self.client._send({"cmd": "pretty"})["pretty"]

    def close(self):
        """Close client connections"""
        self.client.close()
