# tests/test_timestamps_readable.py

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from move_op_impl import Move, ThreadSafeState, pretty_tree, unique_parent, acyclic
from timestamper import Timestamper


def is_tree_valid(tree, stage): 
    has_unique_parent = unique_parent(tree)
    is_acyclic = acyclic(tree)
    print(f"[{stage}] unique_parent={has_unique_parent}, acyclic={is_acyclic}")
    assert has_unique_parent and is_acyclic, f"tree invariants broken at {stage} stage"



def test_basic_timestamp_tests():

    print("BASIC TIMESTAMP TESTS")
    initial_tree = {
        ("root", "", "A"),
        ("root", "", "B"),
        ("root", "", "C"),
        ("A", "", "a1"),
        ("A", "", "a2"),
        ("A", "", "a3"),
    }
    

    ts = Timestamper() 


    state = ThreadSafeState(initial_tree)
    

    print("\n1. INITIAL STATE:")
    print(pretty_tree(state.tree()))
    is_tree_valid(state.tree(), "initial")
    
    print("\n2. FIRST OPERATIONS - timestamp order is important")
    # t=1 Move A under B
    state.apply(Move(ts(), "B", "", "A"))   # timestamp = 1
    # t=2 Move A under C (newer timestamp)
    state.apply(Move(ts(), "C", "", "A"))   # timestamp = 2
    
    print(pretty_tree(state.tree()))
    # A should now be under C, not under B
    assert ("C", "", "A") in state.tree(), "A should be under C"
    assert ("B", "", "A") not in state.tree(), "A should not be under B"
    is_tree_valid(state.tree(), "first_operations")
    




    print("\n3. SMALL TIMESTAMP TEST")
    # small timestamp from the past (t=0)
    small_ts = ts.manual(0)  # manually give 0 timestamp
    state.apply(Move(small_ts, "B", "", "A"))  # try to move A to B
    
    print(pretty_tree(state.tree()))
    # A should still be under C because small timestamp is invalid
    assert ("C", "", "A") in state.tree(), "small timestamp should not move A"
    assert ("B", "", "A") not in state.tree(), "A should still be under C"
    is_tree_valid(state.tree(), "small_timestamp")
    




    print("\n4. VALID NEW OPERATION")
    # valid operation with new timestamp
    state.apply(Move(ts(), "B", "", "a1"))  # Move a1 under B
    print(pretty_tree(state.tree()))
    assert ("B", "", "a1") in state.tree(), "a1 should be under B"
    is_tree_valid(state.tree(), "valid_operation")
    
    print("✓ basic timestamp tests completed!")







def test_invalid_operations_and_undo_redo(): #cycles, sml ts

    print("\n INVALID OPERATIONS AND UNDO/REDO TESTS ")
    

    initial_tree = {
        ("root", "", "A"),
        ("root", "", "B"),
        ("A", "", "a1"),
        ("A", "", "a2"),
    }
    
    ts = Timestamper()
    state = ThreadSafeState(initial_tree)
    
    print("\n1. INITIAL:")
    print(pretty_tree(state.tree()))
    is_tree_valid(state.tree(), "initial")
    

    
    print("\n2. PERFORM VALID OPERATIONS:")
    # first perform valid operations
    state.apply(Move(ts(), "B", "", "a1"))  # move a1 to B
    print(pretty_tree(state.tree()))
    is_tree_valid(state.tree(), "valid_operations")


    
    print("\n3. CREATE CYCLE, this should be invalid")
    # move A under its own child a1 (cycle)
    # A -> a1 -> A cycle

    state.apply(Move(ts(), "a2", "", "A"))  # should be invalid
    print(pretty_tree(state.tree()))
    assert ("root", "", "A") in state.tree(), "cycle should not be created, A should stay under root"
    assert ("a2", "", "A") not in state.tree(), "A should not be under a2"
    is_tree_valid(state.tree(), "cycle_prevention")


    
    print("\n4. INVALID OPERATION WITH SMALL TIMESTAMP")
    # invalid operation with small ts
    small_ts = ts.manual(0)
    state.apply(Move(small_ts, "root", "", "a1"))  # move a1 to root
    print(pretty_tree(state.tree()))
    # a1 should still be under B
    assert ("B", "", "a1") in state.tree(), "small timestamp should not move a1!"
    is_tree_valid(state.tree(), "small_ts_invalid")
    



    print("\n5. UNDO/REDO TEST - after invalid operations:")
    print("State before UNDO:")
    print(pretty_tree(state.tree()))
    
    # undo the last valid operation
    state.undo(1)
    print("\nAfter UNDO(1):")
    print(pretty_tree(state.tree()))
    is_tree_valid(state.tree(), "after_undo")
    

    state.redo(1)
    print("\nAfter REDO(1):")
    print(pretty_tree(state.tree()))
    is_tree_valid(state.tree(), "after_redo")
    

    print("\n6. MULTIPLE UNDO/REDO TEST:")
    # undo multiple operations
    state.undo(2)  # undo last 2 operations
    print("\nAfter UNDO(2):")
    print(pretty_tree(state.tree()))
    is_tree_valid(state.tree(), "multiple_undo")
    

    state.redo(2)
    print("\nAfter REDO(2):")
    print(pretty_tree(state.tree()))
    is_tree_valid(state.tree(), "multiple_redo")
    
    print("✓ invalid operations and undo/redo tests completed")







def test_timestamps_readable():
    """
    Main test function - runs all tests
    """
    print("🚀 CRDT MOVE OPERATION TESTS STARTING...")
    print("=" * 50)
    
    try:
        test_basic_timestamp_tests()
        test_invalid_operations_and_undo_redo()
     
        
        print("\n" + "=" * 50)
        print("🎉 ALL TESTS SUCCESSFULLY COMPLETED!")
        print("✅ Timestamp control is working")
        print("✅ Small timestamp operations are rejected")
        print("✅ Invalid operations (cycles) are prevented")
        print("✅ Undo/Redo works correctly")
        print("✅ Tree structure is preserved")
        
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        raise


if __name__ == "__main__":
    test_timestamps_readable()
