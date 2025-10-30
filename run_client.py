from moveclient import MoveClient

if __name__ == "__main__":
    client = MoveClient(
        server_req="tcp://127.0.0.1:5555",
        server_sub="tcp://127.0.0.1:5556"
    )

    # Example: send a move
    resp = client.apply("root", "meta1", "child1")
    print("Apply response:", resp)

    # Snapshot of current tree
    snap = client.snapshot()
    print("Snapshot:", snap)

    # Pretty print
    print(client.pretty())

