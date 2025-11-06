from __future__ import annotations
import json
import time
import uuid
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
import threading
import zmq
from move_op import *
from timestamper import *
from server_my import *



def to_jsonable(Move):                                      
    if isinstance(Move, set):
        # sets of tuples -> list of lists for JSON
        return [to_jsonable(x) for x in Move]
    if isinstance(Move, tuple):
        return [to_jsonable(x) for x in Move]
    if isinstance(Move, list):
        return [to_jsonable(x) for x in Move]
    if isinstance(Move, dict):
        return {k: to_jsonable(v) for k, v in Move.items()}
    return Move

def move_to_dict(m: Move) -> Dict[str, Any]:
    return {
        "move_time": m.move_time,
        "move_parent": m.move_parent,
        "move_meta": m.move_meta,
        "move_child": m.move_child,
    }

def move_from_dict(d: Dict[str, Any]) -> Move:
    return Move(d["move_time"], d["move_parent"], d["move_meta"], d["move_child"])

def logmove_to_dict(lm: LogMove) -> Dict[str, Any]:
    return {
        "log_time": lm.log_time,
        "old_parent": lm.old_parent,   # tuple or None is fine, will be JSON-ified
        "new_parent": lm.new_parent,
        "log_meta": lm.log_meta,
        "log_child": lm.log_child,
    }

def logmove_from_dict(d: Dict[str, Any]) -> LogMove:
    return LogMove(d["log_time"], tuple(d["old_parent"]) if d["old_parent"] is not None else None,
                   d["new_parent"], d["log_meta"], d["log_child"])

def tree_to_list(tree: Set[Tuple[Any, Any, Any]]) -> List[List[Any]]:
    return [[p, m, c] for (p, m, c) in tree]

def tree_from_list(lst: List[List[Any]]) -> Set[Tuple[Any, Any, Any]]:
    return { (p, m, c) for (p, m, c) in lst }


class LamportClock:
    def __init__(self, initial: int = 0):
        self._lock = threading.Lock()
        self._t = int(initial)

    def now(self) -> int:
        with self._lock:
            return self._t

    def tick(self) -> int:
        with self._lock:
            self._t += 1
            return self._t

    def update_on_receive(self, received_ts: int) -> int:
        with self._lock:
            self._t = max(self._t, int(received_ts)) + 1
            return self._t