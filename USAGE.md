# CRDT System Usage Guide

This guide shows you how to actually use the CRDT system for distributed tree editing.

## Installation

```bash
pip install -r requirements.txt
```

## Architecture Options

You have **two ways** to use the system:

### 1. Client-Server Architecture (Centralized)

One server manages state, multiple clients connect to it.

### 2. P2P Architecture (Decentralized)

Multiple peer nodes communicate directly with each other.

---

## Option 1: Client-Server Usage

### Step 1: Start the Server

```python
from server_my import CRDTServer
import time

# Start server on ports 5555 (requests) and 5556 (broadcasts)
server = CRDTServer(rep_port=5555, pub_port=5556)
time.sleep(1)  # Give it time to start

# Server runs in background thread
# Keep it running or use: server.close() to stop
```

### Step 2: Create Clients

```python
from moveclient import MoveClient

# Client 1
client1 = MoveClient(
    server_req="tcp://127.0.0.1:5555",  # Server request port
    server_sub="tcp://127.0.0.1:5556",  # Server broadcast port
    identity="client1"
)

# Client 2
client2 = MoveClient(
    server_req="tcp://127.0.0.1:5555",
    server_sub="tcp://127.0.0.1:5556",
    identity="client2"
)
```

### Step 3: Use the API

```python
# Apply a move: move child "A" to parent "B" with metadata ""
client1.api.apply("B", "", "A")

# Apply batch operations
batch = [("C", "", "a1"), ("D", "", "b1")]
client1.api.apply_batch(batch)

# Undo last operation
client1.api.undo(1)

# Redo
client1.api.redo(1)

# View tree state
print(client1.api.pretty())

# Get snapshot
snapshot = client1.api.snapshot()
```

### Step 4: Listen to Updates

```python
def on_update(topic, data):
    print(f"Received {topic}: {data}")

client1.on("applied", on_update)
client1.on("applied_batch", on_update)
```

### Complete Example

```python
from server_my import CRDTServer
from moveclient import MoveClient
import time

# Start server
server = CRDTServer(rep_port=5555, pub_port=5556)
time.sleep(1)

try:
    # Create clients
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

    # Client 1 operations
    client1.api.apply("B", "", "A")
    print("Client 1 tree:", client1.api.pretty())

    # Client 2 operations
    client2.api.apply("C", "", "a1")
    print("Client 2 tree:", client2.api.pretty())

    # Both see the same state eventually
    time.sleep(0.5)
    print("Final state:", client1.api.pretty())

finally:
    client1.close()
    client2.close()
    server.close()
```

---

## Option 2: P2P Usage

### Step 1: Create Peer Nodes

```python
from p2p_node import PubSubMoveNode

# Peer 1: publishes on 6001, listens on 7001
peer1 = PubSubMoveNode(
    pub_bind="tcp://127.0.0.1:6001",      # Where this peer publishes
    rep_bind="tcp://127.0.0.1:7001",      # Query endpoint
    peer_pub_endpoints=["tcp://127.0.0.1:6002"]  # Connect to peer2's pub
)

# Peer 2: publishes on 6002, listens on 7002
peer2 = PubSubMoveNode(
    pub_bind="tcp://127.0.0.1:6002",
    rep_bind="tcp://127.0.0.1:7002",
    peer_pub_endpoints=["tcp://127.0.0.1:6001"]  # Connect to peer1's pub
)
```

### Step 2: Use Operations

```python
import time
time.sleep(0.2)  # Let sockets connect

# Peer 1 operations
peer1.apply("B", "", "A")  # Move A to B
peer1.apply_batch([("C", "", "a1"), ("D", "", "b1")])
peer1.undo(1)
peer1.redo(1)

# Peer 2 operations
peer2.apply("x", "", "y")

# View state
print("Peer 1:", peer1.pretty())
print("Peer 2:", peer2.pretty())
```

### Step 3: Listen to Peer Messages

```python
def log_received(name):
    def handler(topic, data):
        print(f"[{name}] Received {topic}: {data}")
    return handler

peer1.on("apply", log_received("peer1"))
peer2.on("apply", log_received("peer2"))
```

### Complete P2P Example

```python
from p2p_node import PubSubMoveNode
import time

# Create two peers
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

time.sleep(0.2)

# Peer 1 makes changes
peer1.apply("B", "", "A")
peer1.apply("C", "", "a1")

time.sleep(0.2)

# Both peers should have same state
print("Peer 1 state:\n", peer1.pretty())
print("Peer 2 state:\n", peer2.pretty())

# Cleanup
peer1.close()
peer2.close()
```

---

## Understanding Operations

### Move Operation Format

All moves use: `(parent, meta, child)`
- **parent**: The new parent node ID
- **meta**: Metadata string (often empty "")
- **child**: The node being moved

Example: `("B", "", "A")` means "move node A to be a child of B"

### Tree Structure

The tree is represented as edges: `(parent, meta, child)`
- Each node can have one parent
- Cycles are automatically prevented
- Operations are ordered by Lamport timestamps

### API Methods

**Client-Server (`client.api.*`):**
- `apply(parent, meta, child)` - Apply single move
- `apply_batch([(p1, m1, c1), (p2, m2, c2), ...])` - Batch moves
- `undo(n)` - Undo last n operations
- `redo(n)` - Redo last n operations
- `pretty()` - Get formatted tree string
- `snapshot()` - Get raw tree data

**P2P (`peer.*`):**
- `apply(parent, meta, child)` - Apply and broadcast
- `apply_batch([...])` - Batch apply and broadcast
- `undo(n)` - Undo and broadcast
- `redo(n)` - Redo and broadcast
- `pretty()` - Get formatted tree string
- `on(topic, handler)` - Register event handler

---

## Running Examples

### Quick Start (Client-Server)

```bash
python -c "
from server_my import CRDTServer
from moveclient import MoveClient
import time

server = CRDTServer()
time.sleep(1)
client = MoveClient()
time.sleep(0.5)
client.api.apply('B', '', 'A')
print(client.api.pretty())
client.close()
server.close()
"
```

### Quick Start (P2P)

```bash
python p2p_pubsub_demo.py
```

---

## Tips

1. **Always wait** after creating connections (`time.sleep(0.2-1.0)`) for sockets to connect
2. **Use handlers** to react to remote operations
3. **Check `pretty()`** to visualize tree state
4. **Undo/redo** only works on operations you've performed locally
5. **Cycles are prevented** automatically - invalid moves are silently rejected
6. **Timestamps** are managed automatically via Lamport clocks
