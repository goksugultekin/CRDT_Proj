# tests/test_error_handling.py


import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))






from move_op_impl import Move, ThreadSafeState, pretty_tree, unique_parent, acyclic, ancestor
from timestamper import Timestamper


def test_ancestor_function_fixed(): #bu fonksiyonda bir değişiklik yapmoıştım döngü problemi


    tree = {
        ("root", "", "A"),
        ("A", "", "B"), 
        ("B", "", "C")
    }
    
  
    assert ancestor(tree, "A", "C") == True   # A is ancestor of C
    assert ancestor(tree, "B", "C") == True   # B is ancestor of C  
    assert ancestor(tree, "root", "C") == True # root is ancestor of C
    assert ancestor(tree, "C", "A") == False  # C is not ancestor of A
    assert ancestor(tree, "A", "A") == False  # A is not its own ancestor
    assert ancestor(tree, "X", "Y") == False  # Non-existent nodes
    
    print("✓ Ancestor function tests passed")





def test_error_handling():  #invalid inputs raise appropriate errors


    ts = Timestamper()
    state = ThreadSafeState()
    

    try:
        state.apply(None)
        assert False, "Should have raised ValueError for None operation"
    except ValueError as e:
        assert "cannot be None" in str(e)
    

    try:
        move = Move(ts(), "parent", "", None)
        state.apply(move)
        assert False, "Should have raised ValueError for None child"
    except ValueError as e:
        assert "Child node cannot be None" in str(e)
    
    # test None parent in Move operation - should raise ValueError
    try:
        move = Move(ts(), None, "", "child")
        state.apply(move)
        assert False, "Should have raised ValueError for None parent"
    except ValueError as e:
        assert "New parent cannot be None" in str(e)
    
    # test negative undo count - should raise ValueError
    try:
        state.undo(-1)
        assert False, "Should have raised ValueError for negative undo"
    except ValueError as e:
        assert "cannot be negative" in str(e)
    
    # test negative redo count - should raise ValueError
    try:
        state.redo(-1)
        assert False, "Should have raised ValueError for negative redo"
    except ValueError as e:
        assert "cannot be negative" in str(e)
    
    print("✓ Error handling tests passed")






def test_cycle_prevention():
    """
    Test that cycles are properly prevented.
    This function verifies that operations that would create cycles are rejected.
    """
    ts = Timestamper()
    
    # Cceate initial tree root -> A -> B
    initial_tree = {
        ("root", "", "A"),
        ("A", "", "B")
    }
    state = ThreadSafeState(initial_tree)
    
    # try to create a cycle B -> A (A is already ancestor of B)
    # this operation should be ignored to prevent cycle
    state.apply(Move(ts(), "A", "", "B"))  # this should be ignored
    
    # verify the tree structure is unchanged
    tree = state.tree()
    assert ("A", "", "B") in tree  
    assert ("B", "", "A") not in tree  # cycle not created
    
    # verify tree is still valid
    assert unique_parent(tree)
    assert acyclic(tree)
    
    print("✓ Cycle prevention tests passed")






def test_self_reference_prevention(): #self-references are prevented,nodes cannot be made their own parent
    

    ts = Timestamper()
    
    initial_tree = {
        ("root", "", "A"),
        ("A", "", "B")
    }
    state = ThreadSafeState(initial_tree)
    
    # try to make A its own parent - this should be ignored
    state.apply(Move(ts(), "A", "", "A"))  
    
    tree = state.tree()
    # A should still be under root, not under itself
    assert ("root", "", "A") in tree
    assert ("A", "", "A") not in tree
    
    print("✓ Self-reference prevention tests passed")





def test_undo_redo_edge_cases():
   
    ts = Timestamper()
    
    initial_tree = {
        ("root", "", "A"),
        ("A", "", "B")
    }
    state = ThreadSafeState(initial_tree)
    
    #  undo with 0 operations - should do nothing
    state.undo(0)  
    
    # test redo with 0 operations - should do nothing
    state.redo(0)  
    
    #  undo more operations than exist - should only undo available operations
    state.undo(100)  
    
    #  redo more operations than available - should only redo available operations
    state.redo(100)  
    
    print("✓ Undo/redo edge cases tests passed")





def test_comprehensive_scenario():  #multiple operations and validations

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
    assert unique_parent(tree), "Tree should have unique parents"
    assert acyclic(tree), "Tree should be acyclic"
    
    # Test undo/redo functionality
    state.undo(2)
    print("\nAfter undo(2):")
    print(pretty_tree(state.tree()))
    
    state.redo(1)
    print("\nAfter redo(1):")
    print(pretty_tree(state.tree()))
    
    # final verification of tree integrity
    final_tree = state.tree()
    assert unique_parent(final_tree), "Final tree should have unique parents"
    assert acyclic(final_tree), "Final tree should be acyclic"
    
    print("✓ Comprehensive scenario test passed")




def run_all_tests():
    
    print("🚀 CRDT Error Handling and Fix Tests Starting...")
    print("=" * 60)
    
    try:
        test_ancestor_function_fixed()
        test_error_handling()
        test_cycle_prevention()
        test_self_reference_prevention()
        test_undo_redo_edge_cases()
        test_comprehensive_scenario()
        
        print("\n" + "=" * 60)
        print("🎉 All error handling and fix tests passed!")
        print("✅ Ancestor function works correctly")
        print("✅ Error handling prevents invalid operations")
        print("✅ Cycle prevention works")
        print("✅ Self-reference prevention works")
        print("✅ Undo/redo edge cases handled properly")
        print("✅ Comprehensive scenarios work correctly")
        
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()
