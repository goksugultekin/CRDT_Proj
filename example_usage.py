#!/usr/bin/env python3
"""
Simple example showing how to use the CRDT system.
Run this to see it in action!
"""

import time
from server_my import CRDTServer
from moveclient import MoveClient


def example_client_server():
    """Example using client-server architecture"""
    print("=" * 60)
    print("CLIENT-SERVER EXAMPLE")
    print("=" * 60)
    
    # Step 1: Start the server
    print("\n1. Starting server...")
    server = CRDTServer(rep_port=5555, pub_port=5556)
    time.sleep(1)  # Give server time to start
    
    try:
        # Step 2: Create clients
        print("\n2. Creating clients...")
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
        time.sleep(0.5)
        
        # Step 3: Show initial state
        print("\n3. Initial tree state:")
        print(client1.api.pretty())
        
        # Step 4: Client 1 makes a move
        print("\n4. Client 1: Moving A to B...")
        client1.api.apply("B", "", "A")
        print("   Tree after move:")
        print(client1.api.pretty())
        
        # Step 5: Client 2 makes a different move
        print("\n5. Client 2: Moving a1 to C...")
        client2.api.apply("C", "", "a1")
        time.sleep(0.2)  # Let updates propagate
        
        # Step 6: Both clients see the same state
        print("\n6. Final state (both clients see the same):")
        print("Client 1 view:")
        print(client1.api.pretty())
        print("\nClient 2 view:")
        print(client2.api.pretty())
        
        # Step 7: Test batch operations
        print("\n7. Client 1: Batch operations...")
        batch = [("D", "", "b1"), ("E", "", "c1")]
        client1.api.apply_batch(batch)
        print("   After batch:")
        print(client1.api.pretty())
        
        # Step 8: Test undo/redo
        print("\n8. Client 1: Undo last operation...")
        client1.api.undo(1)
        print("   After undo:")
        print(client1.api.pretty())
        
        print("\n9. Client 1: Redo...")
        client1.api.redo(1)
        print("   After redo:")
        print(client1.api.pretty())
        
        print("\n" + "=" * 60)
        print("Example completed successfully!")
        print("=" * 60)
        
    finally:
        # Cleanup
        print("\nCleaning up...")
        client1.close()
        client2.close()
        server.close()
        time.sleep(0.5)


def example_p2p():
    """Example using P2P architecture"""
    print("\n" + "=" * 60)
    print("P2P EXAMPLE")
    print("=" * 60)
    
    from p2p_node import PubSubMoveNode
    
    # Create two peer nodes
    print("\n1. Creating peer nodes...")
    peer1 = PubSubMoveNode(
        pub_bind="tcp://127.0.0.1:6001",
        rep_bind="tcp://127.0.0.1:7001",
        peer_pub_endpoints=["tcp://127.0.0.1:6002"]
    )
    
    peer2 = PubSubMoveNode(
        pub_bind="tcp://127.0.0.1:6002",
        rep_bind="tcp://127.0.0.1:7002",
        peer_pub_endpoints=["tcp://127.0.0.1:6001"]
    )
    
    time.sleep(0.3)  # Let sockets connect
    
    # Set up logging
    def log_rx(name):
        def handler(topic, data):
            print(f"  [{name} received] {topic}")
        return handler
    
    peer1.on("apply", log_rx("Peer1"))
    peer2.on("apply", log_rx("Peer2"))
    
    print("\n2. Peer 1: Moving A to B...")
    peer1.apply("B", "", "A")
    time.sleep(0.2)
    
    print("\n3. Peer 2: Moving a1 to C...")
    peer2.apply("C", "", "a1")
    time.sleep(0.2)
    
    print("\n4. Both peers should have same state:")
    print("Peer 1 state:")
    print(peer1.pretty())
    print("\nPeer 2 state:")
    print(peer2.pretty())
    
    print("\n" + "=" * 60)
    print("P2P example completed!")
    print("=" * 60)
    
    # Cleanup
    peer1.close()
    peer2.close()
    time.sleep(0.2)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "p2p":
        example_p2p()
    else:
        example_client_server()
        print("\n\nTo run P2P example: python example_usage.py p2p")
