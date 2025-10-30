import time, json
from p2p_pub_sub import PubSubMove 
from move_op_imply import pretty_tree

def on_any(topic, data, node_name, bus):
    tree_str = pretty_tree(bus.state.tree())
    print(f"[{node_name}] <- {topic}: {json.dumps(data)}\n[{node_name}] tree:\n{tree_str}\n")

def main(node_name="nodeA"):
    bus = PubSubMove(pub_addr="tcp://127.0.0.1:5555",
                     sub_addr="tcp://127.0.0.1:5556")
    for t in ["apply","apply_batch","undo","redo"]:
        bus.on(t, lambda topic, data, n=node_name, b=bus: on_any(topic, data, n, b))

    time.sleep(0.5)             
    bus.apply("root", "edge", f"{node_name}-child-1")
    time.sleep(0.2)
    bus.apply(f"{node_name}-child-1", "edge", f"{node_name}-child-2")

    print(f"[{node_name}] sending done. Press Ctrl+C to quit; node will keep receiving.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        
        bus.close()

if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else "nodeA")