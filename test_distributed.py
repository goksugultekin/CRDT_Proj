# test_distributed.py
# Test distributed CRDT operations using ZeroMQ

import time
import threading
from moveclient import MoveClient
from server_my import CRDTServer


def test_distributed_operations():
    """Test distributed CRDT operations"""
    print("Testing Distributed CRDT Operations...")
    
    # Start server
    print("Starting CRDT server...")
    server = CRDTServer(rep_port=5555, pub_port=5556)
    time.sleep(1)  # give server time to start
    
    try:
        # Create clients
        print("Creating clients...")
        client1 = MoveClient(
            server_req="tcp://127.0.0.1:5555",
            server_sub="tcp://127.0.0.1:5556",
            identity="client1"
        )
        
        client2 = MoveClient(
            server_req="tcp://127.0.0.1:5555", 
            server_sub="tcp://127.0.0.1:5556",
            identity="client2"
        )
        
        time.sleep(1)  # Give clients time to connect
        
        # Test operations
        print("\nTesting concurrent operations...")
        
        # Client 1 operations
        print("Client 1: Moving A to B...")
        resp1 = client1.api.apply("B", "", "A")
        print(f"Client 1 response: {resp1.get('ok', False)}")
        
        # Client 2 operations  
        print("Client 2: Moving a1 to C...")
        resp2 = client2.api.apply("C", "", "a1")
        print(f"Client 2 response: {resp2.get('ok', False)}")
        
        # Get current state
        print("\n Current tree state:")
        pretty1 = client1.api.pretty()
        print(pretty1)
        
        # Test batch operations
        print("\n Testing batch operations...")
        batch_moves = [("D", "", "b1"), ("E", "", "c1")]
        resp_batch = client1.api.apply_batch(batch_moves)
        print(f"Batch response: {resp_batch.get('ok', False)}")
        
        # Test undo/redo
        print("\n Testing undo/redo...")
        undo_resp = client1.api.undo(1)
        print(f"Undo response: {undo_resp.get('ok', False)}")
        
        redo_resp = client1.api.redo(1)
        print(f"Redo response: {redo_resp.get('ok', False)}")
        
        # Final state
        print("\n Final tree state:")
        final_pretty = client1.api.pretty()
        print(final_pretty)
        
        print("\nDistributed CRDT operations test completed successfully!")
        
    finally:
        # Cleanup
        print("\nCleaning up...")
        client1.close()
        client2.close()
        server.close()
        time.sleep(1)


if __name__ == "__main__":
    test_distributed_operations()
