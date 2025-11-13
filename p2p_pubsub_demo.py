# p2p_pubsub_demo.py
import time
from p2p_node import PubSubMoveNode

# Peer A: PUB=6001, REP=7001; Peer B'nin PUB'una SUB bağlanıyor
n1 = PubSubMoveNode(
    pub_bind="tcp://127.0.0.1:6001",
    rep_bind="tcp://127.0.0.1:7001",
    peer_pub_endpoints=["tcp://127.0.0.1:6002"],
)

# Peer B: PUB=6002, REP=7002; Peer A'nın PUB'una SUB bağlanıyor
n2 = PubSubMoveNode(
    pub_bind="tcp://127.0.0.1:6002",
    rep_bind="tcp://127.0.0.1:7002",
    peer_pub_endpoints=["tcp://127.0.0.1:6001"],
)

# Konsolede “hangi peer ne aldı?” görmek için basit handler’lar
def log_rx(name):
    def _h(topic, data):
        print(f"[{name} RX] topic={topic} data={data}")
    return _h

for t in ("apply", "apply_batch", "undo", "redo"):
    n1.on(t, log_rx("peerA"))
    n2.on(t, log_rx("peerB"))

time.sleep(0.2)  # soketler bağlansın

print("\n--- publish from A ---")
n1.apply("A", "", "x")          # A -> x
n1.apply_batch([("A", "", "y")])
n1.undo(1)
n1.redo(1)

time.sleep(0.2)

print("\n--- publish from B ---")
n2.apply("x", "", "y")          # x -> y (cycle ise içerde skip edilir)
n2.undo(1)
n2.redo(1)

time.sleep(0.5)

print("\n--- pretty states ---")
print("A state:\n", n1.pretty())
print("B state:\n", n2.pretty())
