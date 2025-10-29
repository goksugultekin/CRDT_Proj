from dataclasses import dataclass
from typing import Any, List, Optional, Set, Tuple, Iterable, Dict
import threading

@dataclass(frozen=True)
class Move:
    move_time: Any
    move_parent: Any
    move_meta: Any
    move_child: Any

@dataclass(frozen=True)
class LogMove:
    log_time: Any
    old_parent: Optional[Tuple[Any, Any]]
    new_parent: Any
    log_meta: Any
    log_child: Any

State = Tuple[List[LogMove], Set[Tuple[Any, Any, Any]]]

def get_parent(tree: Set[Tuple[Any, Any, Any]], child: Any) -> Optional[Tuple[Any, Any]]:
    matches = [(p, m) for (p, m, c) in tree if c == child]
    if len(matches) == 1:
        return matches[0]
    return None

def _children_map(tree: Set[Tuple[Any, Any, Any]]) -> Dict[Any, List[Tuple[Any, Any]]]:
    d: Dict[Any, List[Tuple[Any, Any]]] = {}
    for p, m, c in tree:
        d.setdefault(p, []).append((m, c))
    return d

def ancestor(tree: Set[Tuple[Any, Any, Any]], parent: Any, child: Any) -> bool:


    if parent == child:
        return False  # Bir düğüm kendisinin atası sayılmasın

    children = _children_map(tree)
    stack, seen = [parent], set()

    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)

        if node == child:
            return True

        for _, c in children.get(node, []):
            if c not in seen:
                stack.append(c)

    return False

def do_op(op: Move, tree: Set[Tuple[Any, Any, Any]]):
    
    if op is None:
        raise ValueError("Move operation cannot be None")

    t, newp, m, c = op.move_time, op.move_parent, op.move_meta, op.move_child

    if c is None:
        raise ValueError("Child node cannot be None")
    if newp is None:
        raise ValueError("New parent cannot be None")

    oldp = get_parent(tree, c)
    log = LogMove(t, oldp, newp, m, c)

   
    if c == newp:
        return log, set(tree)

   
    temp_tree = {(p2, m2, c2) for (p2, m2, c2) in tree if c2 != c}
    temp_tree.add((newp, m, c))

    if ancestor(temp_tree, c, newp):
        
        return log, set(tree)

  
    return log, temp_tree

def undo_op(logop: LogMove, tree: Set[Tuple[Any, Any, Any]]):
    if logop is None:
        raise ValueError("LogMove operation cannot be None")

    c = logop.log_child
    if c is None:
        raise ValueError("Child node in log cannot be None")

    base = {(p2, m2, c2) for (p2, m2, c2) in tree if c2 != c}

    if logop.old_parent is None:
        return base

    oldp, oldm = logop.old_parent
    if oldp is None or oldm is None:
        raise ValueError("Invalid old parent in log entry")

    base.add((oldp, oldm, c))
    return base

def redo_op(logop: LogMove, state: State) -> State:
    """Redo a previously undone operation"""
    ops, tree = state
    # Create Move from LogMove
    move = Move(logop.log_time, logop.new_parent, logop.log_meta, logop.log_child)
    # Apply the operation directly without timestamp checking
    # (redo operations are already validated operations from history)
    op2, tree2 = do_op(move, tree)
    # If cycle is detected, do_op returns the same tree unchanged
    # Skip this operation and return state unchanged
    if tree2 == tree:
        return state
    # Add to log (this operation was previously in log, just being reapplied)
    return ([op2] + ops, tree2)

def apply_op(op: Move, state: State) -> State:
    log, tree1 = state
    if not log:
        op2, tree2 = do_op(op, tree1)
        # Only add to log if the operation actually changed the tree
        if tree2 != tree1:
            return ([op2], tree2)
        else:
            return ([], tree1)  # Invalid operation, don't log it
    logop, *ops = log
    if op.move_time < logop.log_time:
        # Small timestamp - reject the operation
        return (log, tree1)  # Don't apply small timestamp operations
    op2, tree2 = do_op(op, tree1)
    # Only add to log if the operation actually changed the tree
    if tree2 != tree1:
        return ([op2] + log, tree2)
    else:
        return (log, tree1)  # Invalid operation, don't log it

def apply_ops(ops: Iterable[Move]) -> State:
    state: State = ([], set())
    for oper in ops:
        state = apply_op(oper, state)
    return state

def unique_parent(tree: Set[Tuple[Any, Any, Any]]) -> bool:
    seen: Dict[Any, Tuple[Any, Any]] = {}
    for p, m, c in tree:
        if c in seen:
            return False
        seen[c] = (p, m)
    return True

def acyclic(tree: Set[Tuple[Any, Any, Any]]) -> bool:
    
    children = _children_map(tree)
    WHITE, GRAY, BLACK = 0, 1, 2
    color: Dict[Any, int] = {}

    nodes = {p for (p, m, c) in tree} | {c for (p, m, c) in tree}

    def dfs(u: Any) -> bool:
        color[u] = GRAY
        for _, v in children.get(u, []):
            col = color.get(v, WHITE)
            if col == GRAY:
                return False  #
            if col == WHITE:
                if not dfs(v):
                    return False
        color[u] = BLACK
        return True

    for n in nodes:
        if color.get(n, WHITE) == WHITE:
            if not dfs(n):
                return False
    return True

def pretty_tree(tree: Set[Tuple[Any, Any, Any]]) -> str:
    children = _children_map(tree)
    roots = {p for (p, m, c) in tree} - {c for (p, m, c) in tree}
    if not roots:
        roots = {p for (p, m, c) in tree}
    lines = []
    def dfs(node: Any, depth: int):
        lines.append("  " * depth + f"- {node}")
        for m, c in sorted(children.get(node, []), key=lambda x: str(x)):
            lines.append("  " * (depth + 1) + f"{m} -> {c}")
            dfs(c, depth + 2)
    for r in sorted(roots, key=lambda x: str(x)):
        dfs(r, 0)
    return "\n".join(lines)

class ThreadSafeState:
    def __init__(self, initial_tree: Optional[Set[Tuple[Any, Any, Any]]] = None):
        if initial_tree is None:
            initial_tree = set()
        self._state: State = ([], set(initial_tree))
        self._redo_stack: List[LogMove] = []
        self._lock = threading.Lock()

    def apply(self, op: Move) -> None:
        if op is None:
            raise ValueError("Move operation cannot be None")
        with self._lock:
            self._redo_stack.clear()
            self._state = apply_op(op, self._state)

    def undo(self, n: int = 1) -> None:
        if n < 0:
            raise ValueError("Number of undos cannot be negative")
        if n == 0:
            return
        with self._lock:
            log, tree = self._state
            for _ in range(n):
                if not log:
                    break
                logop, *rest = log
                tree = undo_op(logop, tree)
                self._redo_stack.append(logop)
                log = rest
            self._state = (log, tree)

    def redo(self, n: int = 1) -> None:
        if n < 0:
            raise ValueError("Number of redos cannot be negative")
        if n == 0:
            return
        with self._lock:
            for _ in range(n):
                if not self._redo_stack:
                    break
                logop = self._redo_stack.pop()
                ops, tree_before = self._state
                new_state = redo_op(logop, self._state)
                _, tree_after = new_state
                # If cycle is detected, redo_op returns state unchanged (tree unchanged)
                # Skip this operation and continue with next one
                if tree_after == tree_before:
                    continue
                self._state = new_state

    def snapshot(self) -> State:
        with self._lock:
            log, tree = self._state
            return (list(log), set(tree))

    def tree(self) -> Set[Tuple[Any, Any, Any]]:
        with self._lock:
            return set(self._state[1])

    def log(self) -> List[LogMove]:
        with self._lock:
            return list(self._state[0])
