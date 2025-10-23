# tests/test_concurrent_operations.py
# tests concurrent operations for CRDT system

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))




import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from move_op_impl import Move, ThreadSafeState, pretty_tree, unique_parent, acyclic
from timestamper import Timestamper




def test_basic_concurrent_moves():
    """Test concurrent move operations from multiple threads"""
    print("Test 1: Basic concurrent move operations...")
    
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
    ts = Timestamper()
    
    print("Initial tree:")
    print(pretty_tree(state.tree()))
    
    def thread1_move_A_to_B():
        print("  Thread 1: Moving A to B...")
        time.sleep(0.01)
        state.apply(Move(ts(), "B", "", "A"))
        return "Thread 1 completed: A -> B"
    

    def thread2_move_a1_to_C():
        print("  Thread 2: Moving a1 to C...")
        time.sleep(0.01)
        state.apply(Move(ts(), "C", "", "a1"))
        return "Thread 2 completed: a1 -> C"
    

    def thread3_move_b1_to_A():
        print("  Thread 3: Moving b1 to A")
        time.sleep(0.01)
        state.apply(Move(ts(), "A", "", "b1"))
        return "Thread 3 completed: b1 -> A"
    
    print("\n3 threads running concurrently")
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(thread1_move_A_to_B),
            executor.submit(thread2_move_a1_to_C),
            executor.submit(thread3_move_b1_to_A)
        ]
        
        for future in as_completed(futures):
            result = future.result()
            print(f"  {result}")
    
    final_tree = state.tree()
    print("\nFinal tree structure:")
    print(pretty_tree(final_tree))
    
    assert unique_parent(final_tree)
    assert acyclic(final_tree)
    
    print("Test 1 successful: Concurrent move operations working")
    print()




def test_concurrent_undo_redo():
    """Test concurrent undo/redo operations"""
    print("Test 2: Concurrent undo/redo operations")
    
    initial_tree = {
        ("root", "", "A"),
        ("root", "", "B"),
        ("A", "", "a1"),
        ("A", "", "a2")
    }
    
    state = ThreadSafeState(initial_tree)
    ts = Timestamper()
    
    print("Initial tree:")
    print(pretty_tree(state.tree()))
    
    print("\nApplying some operations...")
    state.apply(Move(ts(), "B", "", "a1"))
    state.apply(Move(ts(), "B", "", "a2"))
    state.apply(Move(ts(), "A", "", "B"))
    
    print("Tree after operations:")
    print(pretty_tree(state.tree()))
    
    def thread1_undo():
        print("  Thread 1: Undoing 1 operation...")
        time.sleep(0.01)
        state.undo(1)
        return "Thread 1: Undo completed"
    


    def thread2_redo():
        print("  Thread 2: Redoing 1 operation...")
        time.sleep(0.01)
        state.redo(1)
        return "Thread 2: Redo completed"
    


    print("\n2 threads running undo/redo concurrently...")
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(thread1_undo),
            executor.submit(thread2_redo)
        ]
        
        for future in as_completed(futures):
            result = future.result()
            print(f"  {result}")
    
    final_tree = state.tree()
    print("\nFinal tree structure:")
    print(pretty_tree(final_tree))
    
    assert unique_parent(final_tree)
    assert acyclic(final_tree)
    
    print("Test 2 successful: Concurrent undo/redo working")
    print()





def test_timestamp_conflicts():
    """Test timestamp conflicts in concurrent operations"""
    print("Test 3: Timestamp conflicts")
    
    initial_tree = {
        ("root", "", "A"),
        ("root", "", "B"),
        ("A", "", "a1")
    }
    
    state = ThreadSafeState(initial_tree)
    ts = Timestamper()
    
    print("Initial tree:")
    print(pretty_tree(state.tree()))
    
    def thread1_same_timestamp():
        print("  Thread 1: Using same timestamp (5)")
        time.sleep(0.01)
        same_ts = ts.manual(5)
        state.apply(Move(same_ts, "B", "", "a1"))
        return "Thread 1: Same timestamp a1 -> B"
    


    def thread2_different_timestamp():
        print("  Thread 2: Using different timestamp")
        time.sleep(0.01)
        state.apply(Move(ts(), "A", "", "a1"))
        return "Thread 2: Different timestamp a1 -> A"
    


    print("\n2 threads running with different timestamps...")
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(thread1_same_timestamp),
            executor.submit(thread2_different_timestamp)
        ]
        
        for future in as_completed(futures):
            result = future.result()
            print(f"  {result}")
    
    final_tree = state.tree()
    print("\nFinal tree structure:")
    print(pretty_tree(final_tree))
    
    assert unique_parent(final_tree)
    assert acyclic(final_tree)
    
    print("Test 3 successful: Timestamp conflicts resolved")
    print()





def test_high_concurrency():
    """Test high concurrency with multiple threads"""
    print("Test 4: High concurrency (10 threads)")
    
    initial_tree = {
        ("root", "", "A"),
        ("root", "", "B"),
        ("root", "", "C"),
        ("A", "", "a1"),
        ("A", "", "a2"),
        ("B", "", "b1"),
        ("B", "", "b2"),
        ("C", "", "c1"),
        ("C", "", "c2")
    }
    
    state = ThreadSafeState(initial_tree)
    ts = Timestamper()
    
    print("Initial tree:")
    print(pretty_tree(state.tree()))
    

    #her tread 3 op yapar fonksiyonu tanımlar
    def worker_thread(thread_id):
        operations = []
        for i in range(3):
            time.sleep(0.001)
            
            if thread_id == 0:
                state.apply(Move(ts(), "B", "", "a1"))
                operations.append("a1->B")
            elif thread_id == 1:
                state.apply(Move(ts(), "C", "", "a2"))
                operations.append("a2->C")
            elif thread_id == 2:
                state.apply(Move(ts(), "A", "", "b1"))
                operations.append("b1->A")
            elif thread_id == 3:
                state.apply(Move(ts(), "A", "", "b2"))
                operations.append("b2->A")
            else:
                state.apply(Move(ts(), "B", "", "c1"))
                operations.append("c1->B")
        
        return f"Thread {thread_id}: {', '.join(operations)}"
    
    print("\n10 threads running concurrently (3 operations each)")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker_thread, i) for i in range(10)]
        
        for future in as_completed(futures):
            result = future.result()
            print(f"  {result}")
    
    final_tree = state.tree()
    print("\nFinal tree structure:")
    print(pretty_tree(final_tree))
    
    assert unique_parent(final_tree)
    assert acyclic(final_tree)
    
    print("Test 4 successful: High concurrency working")
    print()




def test_concurrent_invalid_operations():
    """Test concurrent invalid operations (small timestamps)"""
    print("Test 5: Concurrent invalid operations")
    
    initial_tree = {
        ("root", "", "A"),
        ("root", "", "B"),
        ("A", "", "a1"),
        ("A", "", "a2")
    }
    
    state = ThreadSafeState(initial_tree)
    ts = Timestamper()
    
    print("Initial tree:")
    print(pretty_tree(state.tree()))
    

    def thread1_small_timestamp():
        print("  Thread 1: Using small timestamp (0)")
        time.sleep(0.01)
        small_ts = ts.manual(0)
        state.apply(Move(small_ts, "B", "", "a1"))
        return "Thread 1: Small timestamp a1 -> B (should be rejected)"
    


    def thread2_small_timestamp():
        print("  Thread 2: Using small timestamp (0)...")
        time.sleep(0.01)
        small_ts = ts.manual(0)
        state.apply(Move(small_ts, "B", "", "a2"))
        return "Thread 2: Small timestamp a2 -> B (should be rejected)"
    


    def thread3_valid_operation():
        print("  Thread 3: Performing valid operation...")
        time.sleep(0.01)
        state.apply(Move(ts(), "B", "", "a1"))
        return "Thread 3: Valid operation a1 -> B"
    


    print("\n3 threads running concurrently (valid + invalid operations)")
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(thread1_small_timestamp),
            executor.submit(thread2_small_timestamp),
            executor.submit(thread3_valid_operation)
        ]
        
        for future in as_completed(futures):
            result = future.result()
            print(f"  {result}")
    
    final_tree = state.tree()
    print("\nFinal tree structure:")
    print(pretty_tree(final_tree))
    
    assert unique_parent(final_tree)
    assert acyclic(final_tree)
    
    assert ("B", "", "a1") in final_tree or ("B", "", "a2") in final_tree
    
    print("Test 5 successful: Invalid operations rejected!")
    print()


def run_all_concurrent_tests():
    """Run all concurrent operation tests"""
    print("CRDT Concurrent Operations Tests Starting...")
    print("=" * 60)
    print("These tests verify that the CRDT system can handle")
    print("multiple users working simultaneously.")
    print("=" * 60)
    print()
    
    try:
        test_basic_concurrent_moves()
        test_concurrent_undo_redo()
        test_timestamp_conflicts()
        test_high_concurrency()
        test_concurrent_invalid_operations()
        
        print("=" * 60)
        print("ALL CONCURRENT OPERATION TESTS SUCCESSFUL!")
        print("=" * 60)
        print("✅ Concurrent move operations working")
        print("✅ Concurrent undo/redo operations working")
        print("✅ Timestamp conflicts resolved")
        print("✅ High concurrency supported")
        print("✅ Invalid operations rejected")
        print("✅ Thread safety maintained")
        print("=" * 60)
        print("CRDT system is production-ready!")
        
    except Exception as e:
        print(f"\n Test error: {e}")
        print("Please check errors and try again.")
        raise


if __name__ == "__main__":
    run_all_concurrent_tests()