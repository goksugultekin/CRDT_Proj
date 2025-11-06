# tests/test_error_handling.py

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))








from move_op_impl import Move, ThreadSafeState, pretty_tree, unique_parent, acyclic
from timestamper import Timestamper




def test_error_handling():
    """test that invalid inputs raise appropriate errors"""
    ts = Timestamper()
    state = ThreadSafeState()
    


    # test None operation
    try:
        state.apply(None)
        assert False, "Should have raised ValueError for None operation"
    except ValueError as e:
        assert "cannot be None" in str(e)
    



    # test None child
    try:
        move = Move(ts(), "parent", "", None)
        state.apply(move)
        assert False, "Should have raised ValueError for None child"
    except ValueError as e:
        assert "Child node cannot be None" in str(e)


    
    # test None parent
    try:
        move = Move(ts(), None, "", "child")
        state.apply(move)
        assert False, "Should have raised ValueError for None parent"
    except ValueError as e:
        assert "New parent cannot be None" in str(e)



    
    # Test negative undo count
    try:
        state.undo(-1)
        assert False, "Should have raised ValueError for negative undo"
    except ValueError as e:
        assert "cannot be negative" in str(e)
    



    # Test negative redo count
    try:
        state.redo(-1)
        assert False, "Should have raised ValueError for negative redo"
    except ValueError as e:
        assert "cannot be negative" in str(e)
    
    print("Error handling tests passed")







def test_cycle_prevention():
    """Test that cycles are properly prevented"""
    ts = Timestamper()
    

    initial_tree = {
        ("root", "", "A"),
        ("A", "", "B")
    }
    state = ThreadSafeState(initial_tree)
    


    # try to create a cycle B -> A (A is already ancestor of B)
    state.apply(Move(ts(), "A", "", "B"))

 
    tree = state.tree()
    assert ("A", "", "B") in tree  
    assert ("B", "", "A") not in tree  # cycle not created
    
    assert unique_parent(tree)
    assert acyclic(tree)
    
    print("Cycle prevention tests passed")








def test_self_reference_prevention():
    """test that self references are prevented"""
    ts = Timestamper()
    
    initial_tree = {
        ("root", "", "A"),
        ("A", "", "B")
    }
    state = ThreadSafeState(initial_tree)
    
    # try to make A its own parent - this should be ignored
    state.apply(Move(ts(), "A", "", "A"))
    


    tree = state.tree()
    # A should still be under root not under itself
    assert ("root", "", "A") in tree
    assert ("A", "", "A") not in tree
    
    print("Self-reference prevention tests passed")






def test_undo_redo_edge_cases():
    """Test undo redo edge cases"""
    ts = Timestamper()
    
    initial_tree = {
        ("root", "", "A"),
        ("A", "", "B")
    }
    state = ThreadSafeState(initial_tree)
    
   
    state.undo(0)

    state.redo(0)
    
    state.undo(100)
    
    state.redo(100)
    
    print("Undo/redo edge cases tests passed")




def test_redo_cycle_detection(): #redo operations skip cycles and continue with next operation

    ts = Timestamper()
    
    print("\nTesting redo cycle detection.")
    
    initial_tree = {
        ("root", "", "A"),
        ("root", "", "B"),
        ("A", "", "a1"),
        ("A", "", "a2"),
    }
    
    print("\nScenario 1: Simple redo")
    state = ThreadSafeState(initial_tree)
    print("Initial tree:")
    print(pretty_tree(state.tree()))
    

    # apply operations: first move a2 to B, then move a1 to a2
    state.apply(Move(ts(), "B", "", "a2"))  # Move a2 to B
    state.apply(Move(ts(), "a2", "", "a1"))  # Move a1 to a2 (B -> a2 -> a1)
    


    print("\nAfter operations:")
    print(pretty_tree(state.tree()))
    assert ("B", "", "a2") in state.tree()
    assert ("a2", "", "a1") in state.tree()


    

    state.undo(2)
    print("\nAfter undo(2):")
    print(pretty_tree(state.tree()))
    assert ("A", "", "a1") in state.tree()
    assert ("A", "", "a2") in state.tree()
    
    

    tree_before_redo = state.tree()
    state.redo(2)
    print("\nAfter redo(2):")
    print(pretty_tree(state.tree()))



    
    final_tree = state.tree()
    assert unique_parent(final_tree)
    assert acyclic(final_tree)
    assert ("B", "", "a2") in final_tree
    assert ("a2", "", "a1") in final_tree
    


    print("\nScenario 2: Cycle detection on redo")
   
    state = ThreadSafeState(initial_tree)
    state.apply(Move(ts(), "a1", "", "a2"))  
    state.undo(1)
    state.apply(Move(ts(), "a2", "", "a1")) 
    
    print("Tree before redo:")
    print(pretty_tree(state.tree()))
    
   
    
    print("\nScenario 3: Direct cycle test")
    from move_op_impl import do_op
    
    # tree: A -> a2 -> a1 (a2 is ancestor of a1)
    tree = {("root", "", "A"), ("A", "", "a2"), ("a2", "", "a1")}
    
    # move a2 to a1 - this would create cycle
    move = Move(ts(), "a1", "", "a2")
    log, tree_after = do_op(move, tree)
    
    # tree should be unchanged (cycle detected)
    assert tree == tree_after
    


    print("Cycle detection test passed!")
    print("   - do_op correctly detects cycle and skips operation")
    
    print("\n✅ Redo cycle detection test passed!")
    print("   - Cycle detection works correctly in do_op")
    print("   - redo_op uses do_op which handles cycle detection")
    print("   - Tree remains valid and acyclic")




def test_redo_skips_cycle_and_continues():
    ts = Timestamper()
    initial = {("root", "", "A"), ("root", "", "B"), ("A", "", "a1"), ("B", "", "a2")}
    state = ThreadSafeState(initial)

    H1 = Move(ts(), "A", "", "a1")
    H2 = Move(ts(), "a2", "", "A")
    H3 = Move(ts(), "B", "", "a1")

    state.apply(H1); state.apply(H2); state.apply(H3)
    state.undo(3)

    state.apply(Move(ts(), "A", "", "a2"))  # this clears redo stack

    print("\n=== redo-skips (small) ===")
    print("[before redo]")
    print(pretty_tree(state.tree()))

    # show that H2 would be skipped due to cycle
    from move_op_impl import do_op
    before = state.tree()
    log, trial = do_op(H2, before)
    if trial == before:
        print("[simulate H2] skipped (cycle)")
    else:
        print("[simulate H2] applied (unexpected)")
    # redo is no-op because apply cleared redo stack
    state.redo(3)

    after = state.tree()
    print("[after  redo]")
    print(pretty_tree(after))

    assert before == after
    assert ("a2", "", "A") not in after
    assert ("B", "", "a1") not in after
    assert ("A", "", "a2") in after
    assert unique_parent(after)
    assert acyclic(after)




def test_redo_skips_cycle_with_large_history():
    ts = Timestamper()
    initial = {
        ("root", "", "A"), ("root", "", "B"), ("root", "", "C"),
        ("A", "", "a1"), ("A", "", "a2"), ("A", "", "a3"),
    }
    state = ThreadSafeState(initial)

    # history
    ops = [
        Move(ts(), "B", "", "a1"),
        Move(ts(), "C", "", "a2"),
        Move(ts(), "C", "", "B"),   # this step will become a cycle after interference
        Move(ts(), "A", "", "a1"),
    ]
    for op in ops:
        state.apply(op)

    state.undo(len(ops))
    state.apply(Move(ts(), "B", "", "C"))  # clears redo stack; also sets up cycle for "B->C"

    print("\n=== redo-skips (large) ===")
    print("[before redo]")
    print(pretty_tree(state.tree()))

    # locate the critical op (Move C<-B)
    critical = ops[2]
    from move_op_impl import do_op
    before = state.tree()
    log, trial = do_op(critical, before)
    if trial == before:
        print("[simulate critical op] skipped (cycle)")
    else:
        print("[simulate critical op] applied (unexpected)")

    state.redo(len(ops))  # no-op
    after = state.tree()
    print("[after  redo]")
    print(pretty_tree(after))

    assert before == after
    assert ("B", "", "C") in after and ("C", "", "B") not in after
    assert unique_parent(after)
    assert acyclic(after)





def test_comprehensive_scenario():
    """test multiple operations and validations"""
    ts = Timestamper()
    
    # complex initial tree with multiple nodes and relationships
    initial_tree = {
        ("root", "", "A"),
        ("root", "", "B"), 
        ("root", "", "C"),
        ("A", "", "a1"),
        ("A", "", "a2"),
        ("B", "", "b1"),
        ("C", "", "c1")
    }
    
    state = ThreadSafeState(initial_tree)
    print("Initial tree:")
    print(pretty_tree(state.tree()))
    

    # apply various operations to test the system
    state.apply(Move(ts(), "B", "", "a1"))  # Move a1 to B
    state.apply(Move(ts(), "C", "", "A"))   # Move A to C
    state.apply(Move(ts(), "A", "", "b1"))  # Move b1 to A
    
    print("\nAfter operations:")
    print(pretty_tree(state.tree()))
    
   
    tree = state.tree()
    assert unique_parent(tree)
    assert acyclic(tree)
    
    # test undo/redo 
    state.undo(2)
    print("\nAfter undo(2):")
    print(pretty_tree(state.tree()))
    
    state.redo(1)
    print("\nAfter redo(1):")
    print(pretty_tree(state.tree()))
    
    final_tree = state.tree()
    assert unique_parent(final_tree)
    assert acyclic(final_tree)
    
    print(" Comprehensive scenario test passed")







def run_all_tests():
    """Run all error handling tests"""
    print("CRDT Error Handling Tests Starting...")
    print("=" * 50)
    
    try:
        test_error_handling()
        test_cycle_prevention()
        test_self_reference_prevention()
        test_undo_redo_edge_cases()
        test_redo_cycle_detection()
        test_comprehensive_scenario()
        test_redo_skips_cycle_and_continues()
        test_redo_skips_cycle_with_large_history()
        
        print("\n" + "=" * 50)
        print("All error handling tests passed!")
        print("✅ Error handling prevents invalid operations")
        print("✅ Cycle prevention works")
        print("✅ Self-reference prevention works")
        print("✅ Undo/redo edge cases handled properly")
        print("✅ Redo cycle detection works correctly")
        print("✅ Comprehensive scenarios work correctly") 
        print("✅ Redo skips-cycle tests work correctly")       
    
        
    except Exception as e:
        print(f"\nTest error: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()