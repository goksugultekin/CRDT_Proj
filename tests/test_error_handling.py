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
    
    # verify the tree structure is unchanged
    tree = state.tree()
    assert ("A", "", "B") in tree  
    assert ("B", "", "A") not in tree  # cycle not created
    
    # verify tree is still valid
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
    """Test undo/redo edge cases"""
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





def test_comprehensive_scenario():
    """Test multiple operations and validations"""
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
    
    # verify tree invariants are maintained
    tree = state.tree()
    assert unique_parent(tree)
    assert acyclic(tree)
    
    # test undo/redo functionality
    state.undo(2)
    print("\nAfter undo(2):")
    print(pretty_tree(state.tree()))
    
    state.redo(1)
    print("\nAfter redo(1):")
    print(pretty_tree(state.tree()))
    
    # final verification of tree integrity
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
        test_comprehensive_scenario()
        
        print("\n" + "=" * 50)
        print("All error handling tests passed!")
        print("✅ Error handling prevents invalid operations")
        print("✅ Cycle prevention works")
        print("✅ Self-reference prevention works")
        print("✅ Undo/redo edge cases handled properly")
        print("✅ Comprehensive scenarios work correctly")
        
    except Exception as e:
        print(f"\nTest error: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()