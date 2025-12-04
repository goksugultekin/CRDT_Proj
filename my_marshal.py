from __future__ import annotations
from typing import Any, Dict, List, Optional, Set, Tuple
import threading


# ---------- JSON helpers ----------

def to_jsonable(x: Any):
    if isinstance(x, set):
        return [to_jsonable(i) for i in x]
    if isinstance(x, tuple):
        return [to_jsonable(i) for i in x]
    if isinstance(x, list):
        return [to_jsonable(i) for i in x]
    if isinstance(x, dict):
        return {k: to_jsonable(v) for k, v in x.items()}
    return x


def move_to_dict(m: Any) -> Dict[str, Any]:
    return {
        "move_time": getattr(m, "move_time"),
        "move_parent": getattr(m, "move_parent"),
        "move_meta": getattr(m, "move_meta"),
        "move_child": getattr(m, "move_child"),
    }


def move_from_dict(d: Dict[str, Any]):
    # Lazy import to avoid cycles
    from move_op_impl import Move
    return Move(d["move_time"], d["move_parent"], d["move_meta"], d["move_child"])


def logmove_to_dict(lm: Any) -> Dict[str, Any]:
    return {
        "log_time": getattr(lm, "log_time"),
        "old_parent": getattr(lm, "old_parent"),
        "new_parent": getattr(lm, "new_parent"),
        "log_meta": getattr(lm, "log_meta"),
        "log_child": getattr(lm, "log_child"),
    }


def logmove_from_dict(d: Dict[str, Any]):
    from move_op_impl import LogMove
    old_parent = tuple(d["old_parent"]) if d.get("old_parent") is not None else None
    return LogMove(d["log_time"], old_parent, d["new_parent"], d["log_meta"], d["log_child"])


def tree_to_list(tree: Set[Tuple[Any, Any, Any]]) -> List[List[Any]]:
    return [[p, m, c] for (p, m, c) in tree]


def tree_from_list(lst: List[List[Any]]) -> Set[Tuple[Any, Any, Any]]:
    return {(p, m, c) for (p, m, c) in lst}


# ---------- Lamport Clock (shared util) ----------

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
