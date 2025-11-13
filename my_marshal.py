# Serialization utilities for CRDT operations

from __future__ import annotations
import json
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Dict, List, Set, Tuple, Optional
from move_op_impl import Move, LogMove

def to_jsonable(o):
    if is_dataclass(o):
        o = asdict(o)
    if isinstance(o, set):
        return [to_jsonable(x) for x in o]
    if isinstance(o, tuple):
        return [to_jsonable(x) for x in o]
    if isinstance(o, list):
        return [to_jsonable(x) for x in o]
    if isinstance(o, dict):
        return {k: to_jsonable(v) for k, v in o.items()}
    return o

def move_to_dict(m: Move) -> Dict[str, Any]:
    return {
        "move_time": m.move_time,
        "move_parent": m.move_parent,
        "move_meta": m.move_meta,
        "move_child": m.move_child,
        "op_id": m.op_id,
    }

def move_from_dict(d: Dict[str, Any]) -> Move:
    return Move(
        d["move_time"],
        d["move_parent"],
        d["move_meta"],
        d["move_child"],
        d.get("op_id"),
    )

def logmove_to_dict(lm: LogMove) -> Dict[str, Any]:
    return {
        "log_time": lm.log_time,
        "old_parent": lm.old_parent,
        "new_parent": lm.new_parent,
        "log_meta": lm.log_meta,
        "log_child": lm.log_child,
    }

def logmove_from_dict(d: Dict[str, Any]) -> LogMove:
    return LogMove(
        d["log_time"],
        tuple(d["old_parent"]) if d.get("old_parent") is not None else None,
        d["new_parent"],
        d["log_meta"],
        d["log_child"],
    )

def tree_to_list(tree: Set[Tuple[Any, Any, Any]]) -> List[List[Any]]:
    return [[p, m, c] for (p, m, c) in tree]

def tree_from_list(lst: List[List[Any]]) -> Set[Tuple[Any, Any, Any]]:
    return {(p, m, c) for (p, m, c) in lst}
