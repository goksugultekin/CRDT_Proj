# Import the client
from moveclient import MoveClient
import time
from move_op import *
from server_my import *
from moveclient import *
from timestamper import *

# Create a client
client = MoveClient(identity="alice")
clientThread = ThreadSafeState()
time.sleep(0.5)  # Give it time to connect

# Create your first tree nodes
# Format: client.apply(parent, edge_label, child)
client.apply("root", "edge1", "Alice")
time.sleep(0.2)

# View the tree
print(MoveClient.pretty(client))

# Add more nodes
client.apply("root", "edge2", "Bob")
client.apply("Alice", "edge3", "Charlie")
time.sleep(0.2)

print("\nTree after adding more nodes:")
print(client.pretty())

# Move Bob under Alice
