

# tests/test_error_handling.py
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from move_op_impl import Move, ThreadSafeState, pretty_tree, unique_parent, acyclic
from timestamper import Timestamper






def scenario3_initial_tree():
    return {
        ("root", "", "A"), ("root", "", "B"), ("root", "", "C"),
        ("A", "", "a1"), ("A", "", "a2"), ("A", "", "a3"),
    }

def scenario3_history_ops(ts: Timestamper):
    
    return [
        Move(ts(), "B", "", "a2"), 
        Move(ts(), "C", "", "a2"), 
        Move(ts(), "C", "", "B"),   # B -> C cycle
        Move(ts(), "A", "", "a1"),  # a1 -> A
    ]

def scenario3_new_ops(ts: Timestamper):
  
    return [
        Move(ts(), "B", "", "C"),  
        Move(ts(), "B", "", "a3"),  
        Move(ts(), "C", "", "B"),    
        Move(ts(), "root", "", "a1") 
    ]




def test_error_handling():
    ts = Timestamper()
    state = ThreadSafeState()

    # None operation
    try:
        state.apply(None)
        assert False
    except ValueError as e:
        assert "cannot be None" in str(e)

    # None child
    try:
        state.apply(Move(ts(), "parent", "", None))
        assert False
    except ValueError as e:
        assert "Child node cannot be None" in str(e)

    # None parent
    try:
        state.apply(Move(ts(), None, "", "child"))
        assert False
    except ValueError as e:
        assert "New parent cannot be None" in str(e)

    # Negative undo
    try:
        state.undo(-1)
        assert False
    except ValueError as e:
        assert "cannot be negative" in str(e)

    # Negative redo
    try:
        state.redo(-1)
        assert False
    except ValueError as e:
        assert "cannot be negative" in str(e)


def test_cycle_prevention():
    ts = Timestamper()
    initial_tree = {("root", "", "A"), ("A", "", "B")}
    state = ThreadSafeState(initial_tree)

    # B -> A denemesi (A, B'nin atası)
    state.apply(Move(ts(), "A", "", "B"))
    tree = state.tree()
    assert ("A", "", "B") in tree
    assert ("B", "", "A") not in tree
    assert unique_parent(tree) and acyclic(tree)


def test_self_reference_prevention():
    ts = Timestamper()
    initial_tree = {("root", "", "A"), ("A", "", "B")}
    state = ThreadSafeState(initial_tree)

    # A kendi ebeveyni olamaz
    state.apply(Move(ts(), "A", "", "A"))
    tree = state.tree()
    assert ("root", "", "A") in tree
    assert ("A", "", "A") not in tree
    assert unique_parent(tree) and acyclic(tree)


def test_undo_redo_edge_cases():
    ts = Timestamper()
    initial_tree = {("root", "", "A"), ("A", "", "B")}
    state = ThreadSafeState(initial_tree)

    state.undo(0)
    state.redo(0)
    state.undo(100)
    state.redo(100)

    tree = state.tree()
    assert unique_parent(tree) and acyclic(tree)


def test_redo_cycle_detection():
    ts = Timestamper()
    initial_tree = {
        ("root", "", "A"),
        ("root", "", "B"),
        ("A", "", "a1"),
        ("A", "", "a2"),
    }

    # Senaryo 1
    state = ThreadSafeState(initial_tree)
    state.apply(Move(ts(), "B", "", "a2"))
    state.apply(Move(ts(), "a2", "", "a1"))
    state.undo(2)
    state.redo(2)
    t = state.tree()
    assert ("B", "", "a2") in t and ("a2", "", "a1") in t
    assert unique_parent(t) and acyclic(t)

    # Senaryo 2 (cycle 
    state = ThreadSafeState(initial_tree)
    state.apply(Move(ts(), "a1", "", "a2"))  # a1 -> a2
    state.undo(1)
    state.apply(Move(ts(), "a2", "", "a1"))  # a2 -> a1 
    state.redo(1)
    after = state.tree()
    assert ("a2", "", "A") not in after
    assert ("B", "", "a1") not in after
    assert ("A", "", "a2") in after
    assert unique_parent(after) and acyclic(after)


def test_redo_skips_cycle_with_large_history():
    ts = Timestamper()
    initial = scenario3_initial_tree()
    state = ThreadSafeState(initial)

  
    ops = scenario3_history_ops(ts)
    for mv in ops:
        state.apply(mv)


    for _ in ops:
        state.undo(1)


    new_ops = scenario3_new_ops(ts)
    for mv in new_ops:
        state.apply(mv)


    before = state.tree()
    state.redo(10)
    after = state.tree()
    assert before == after


    t = state.tree()
    assert ("B", "", "C") in t        
    assert ("C", "", "B") not in t    
    assert ("B", "", "a3") in t       
    assert ("root", "", "a1") in t    
    assert unique_parent(t) and acyclic(t)


    state.undo(2)
    mid = state.tree()
    assert unique_parent(mid) and acyclic(mid)

    state.redo(2)
    final_tree = state.tree()
    assert unique_parent(final_tree) and acyclic(final_tree)


def test_redo_simulation_with_do_op():
    ts = Timestamper()
    initial = {
        ("root", "", "A"),
        ("root", "", "B"),
        ("A", "", "a1"),
        ("A", "", "a2"),
    }
    tree = set(initial)

    from move_op_impl import do_op
    move1 = Move(ts(), "B", "", "a1")
    move2 = Move(ts(), "a2", "", "A")  # cycle 
    move3 = Move(ts(), "B", "", "a2")


    tree.add(("A", "", "a2"))

    _, tree = do_op(move1, tree)  
    before = set(tree)
    _, tree2 = do_op(move2, tree)  # cycle değişmemeli
    assert tree2 == before
    _, tree = do_op(move3, tree) 

    assert ("a2", "", "A") not in tree
    assert ("B", "", "a1") in tree and ("B", "", "a2") in tree
    assert unique_parent(tree) and acyclic(tree)


def test_comprehensive_scenario():
    ts = Timestamper()
    initial_tree = {
        ("root", "", "A"),
        ("root", "", "B"),
        ("root", "", "C"),
        ("A", "", "a1"),
        ("A", "", "a2"),
        ("B", "", "b1"),
        ("C", "", "c1"),
    }

    state = ThreadSafeState(initial_tree)
    state.apply(Move(ts(), "B", "", "a1"))  # a1 -> B
    state.apply(Move(ts(), "C", "", "A"))   # A  -> C
    state.apply(Move(ts(), "A", "", "b1"))  # b1 -> A

    tree = state.tree()
    assert unique_parent(tree) and acyclic(tree)

    state.undo(2)
    state.redo(1)

    final_tree = state.tree()
    assert unique_parent(final_tree) and acyclic(final_tree)


# -------------------- DEMO --------------------

def _print_tree_block(title: str, state: ThreadSafeState):
    print(title)
    print(pretty_tree(state.tree()))
    print()  # boş satır


def _demo_main():
    ts = Timestamper()

    # Demo 1
    initial1 = {
        ("root", "", "A"),
        ("root", "", "B"),
        ("A", "", "a1"),
        ("A", "", "a2"),
    }
    s1 = ThreadSafeState(initial1)
    _print_tree_block("== Demo 1: initial ==", s1)

    s1.apply(Move(ts(), "B", "", "a2"))   # a2 -> B
    s1.apply(Move(ts(), "a2", "", "A"))   # A <- a2 (cycle => atlanır)
    _print_tree_block("== Demo 1: after ops ==", s1)

    s1.undo(1); _print_tree_block("== Demo 1: after undo(1) ==", s1)
    s1.redo(1); _print_tree_block("== Demo 1: after redo(1) ==", s1)

    # Demo 2
    initial2 = {
        ("root", "", "A"), ("root", "", "B"), ("root", "", "C"),
        ("A", "", "a1"), ("A", "", "a2"),
        ("B", "", "b1"),
        ("C", "", "c1"),
    }
    s2 = ThreadSafeState(initial2)
    _print_tree_block("== Demo 2: initial ==", s2)
    s2.apply(Move(ts(), "B", "", "C"))
    s2.apply(Move(ts(), "B", "", "a2"))
    _print_tree_block("== Demo 2: after ops ==", s2)
    s2.undo(2); _print_tree_block("== Demo 2: after undo(2) ==", s2)
    s2.redo(2); _print_tree_block("== Demo 2: after redo(2) ==", s2)

    # Demo 3
    s3 = ThreadSafeState(scenario3_initial_tree())
    _print_tree_block("== Demo 3: initial ==", s3)

    hist_ops = scenario3_history_ops(ts)
    for i, mv in enumerate(hist_ops, 1):
        s3.apply(mv)
        print(f"-- op#{i}: {mv.move_child} -> {mv.move_parent}")
        _print_tree_block(f"== Demo 3: after history op #{i} ==", s3)

    for _ in hist_ops:
        s3.undo(1)
    _print_tree_block("== Demo 3: after undo(all history) ==", s3)

    for i, mv in enumerate(scenario3_new_ops(ts), 1):
        s3.apply(mv)
        print(f"-- new-op#{i}: {mv.move_child} -> {mv.move_parent}")
        _print_tree_block(f"== Demo 3: after new op #{i} ==", s3)

    s3.redo(10); _print_tree_block("== Demo 3: after redo(10) (no effect) ==", s3)
    s3.undo(2); _print_tree_block("== Demo 3: after undo(2) ==", s3)
    s3.redo(2); _print_tree_block("== Demo 3: after redo(2) ==", s3)


# -------------------- MAIN --------------------
def _run_main():
    import argparse, pytest
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--demo", action="store_true",
                        help="Demo run")
    args = parser.parse_args()

    if args.demo:
        print("\n DEMO MODU:\n")
        _demo_main()
        return 0

    print("Running: test_redo_skips_cycle_with_large_history\n")
    return pytest.main(["-s", __file__ + "::test_redo_skips_cycle_with_large_history"])

if __name__ == "__main__":
    raise SystemExit(_run_main())
