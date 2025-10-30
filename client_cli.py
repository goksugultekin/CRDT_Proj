import sys
import argparse
import json
from 

if __name__ == "__main__":
    # 1. Setup the main parser
    parser = argparse.ArgumentParser(
        description="A command-line interface for the PubSubMove."
    )
    # Add optional server connection arguments
    parser.add_argument(
        "--req", 
        default="tcp://127.0.0.1:5555", 
        help="Server REQ address (default: tcp://127.0.0.1:5555)"
    )
    parser.add_argument(
        "--sub", 
        default="tcp://127.0.0.1:5556", 
        help="Server SUB address (default: tcp://127.0.0.1:5556)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute", required=True)

    # --- 'apply' command ---
    apply_parser = subparsers.add_parser("apply", help="Apply a single move operation")
    apply_parser.add_argument("parent", help="The ID of the new parent node")
    apply_parser.add_argument("meta", help="The metadata for the move (e.g., 'edge_label')")
    apply_parser.add_argument("child", help="The ID of the child node to move")

    # --- 'apply_batch' command ---
    batch_parser = subparsers.add_parser(
        "apply_batch", 
        help="Apply a batch of moves. Provide as a list of (p m c p m c...)"
    )
    batch_parser.add_argument(
        "moves", 
        nargs='*', 
        help="List of (parent, meta, child) triplets"
    )

    # --- 'undo' command ---
    undo_parser = subparsers.add_parser("undo", help="Undo N previous operations")
    undo_parser.add_argument(
        "-n", 
        type=int, 
        default=1, 
        help="Number of operations to undo (default: 1)"
    )

    # --- 'redo' command ---
    redo_parser = subparsers.add_parser("redo", help="Redo N undone operations")
    redo_parser.add_argument(
        "-n", 
        type=int, 
        default=1, 
        help="Number of operations to redo (default: 1)"
    )

    # --- 'snapshot' command ---
    snap_parser = subparsers.add_parser(
        "snapshot", 
        help="Get a snapshot of the current state (log and tree)"
    )

    # --- 'pretty' command ---
    pretty_parser = subparsers.add_parser(
        "pretty", 
        help="Get a pretty-printed representation of the tree"
    )

    try:
        args = parser.parse_args()
    except Exception as e:
        print(f"Error parsing arguments: {e}", file=sys.stderr)
        sys.exit(1)

    # 4. Create the client
    client = PubSubMove(
        server_req=args.req,
        server_sub=args.sub
    )

    result = None
    try:
        # 5. Execute the correct command
        if args.command == "apply":
            result = client.apply(args.parent, args.meta, args.child)
        
        elif args.command == "undo":
            result = client.undo(args.n)
            
        elif args.command == "redo":
            result = client.redo(args.n)
            
        elif args.command == "snapshot":
            result = client.snapshot()
            
        elif args.command == "pretty":
            resp = client.pretty()
            print(resp.get("pretty", "Error: No pretty output received."))
        
        elif args.command == "apply_batch":
            if not args.moves or len(args.moves) % 3 != 0:
                print(
                    f"Error: apply_batch needs arguments in triplets (parent meta child). "
                    f"Got {len(args.moves)} items.", 
                    file=sys.stderr
                )
                sys.exit(1)
            
            moves_list = []
            for i in range(0, len(args.moves), 3):
                moves_list.append((args.moves[i], args.moves[i+1], args.moves[i+2]))
            
            result = client.apply_batch(moves_list)

        # 6. Print the JSON result (for most commands)
        if result:
            print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"An error occurred during client operation: {e}", file=sys.stderr)
    
    finally:
        # 7. Always close the client
        client.close()