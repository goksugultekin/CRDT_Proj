# run_node.py
import json, sys, time
from p2p_node import PubSubMoveNode

def _clean(cmdline: str) -> list[str]:

    line = cmdline.strip()
    if line.startswith(">"):
        line = line[1:]
    # normalize spaces
    parts = [p for p in line.replace("-", "_").split() if p]
    return parts

def _print_help():
    print("Komutlar:")
    print("  move <parent> <meta> <child>")
    print("  undo [n]   |  redo [n]")
    print("  tree       |  pretty")
    print("  quit (q)   |  help (h)")
    print()

def main():
    if len(sys.argv) != 2:
        print("usage: python run_node.py config_node_*.json")
        sys.exit(1)

    cfg_path = sys.argv[1]
    with open(cfg_path, "r") as f:
        cfg = json.load(f)

    my_id = cfg["my_id"]
    peers = cfg["peers"]

    me = next(p for p in peers if p["id"] == my_id)
    others = [p for p in peers if p["id"] != my_id]

    pub_bind = f"tcp://{me['ip']}:{me['pub_port']}"
    rep_bind = f"tcp://{me['ip']}:{me['sync_port']}"
    peer_pub_eps = [f"tcp://{p['ip']}:{p['pub_port']}" for p in others]

    node = PubSubMoveNode(
        pub_bind=pub_bind,
        rep_bind=rep_bind,
        peer_pub_endpoints=peer_pub_eps,
        initial_tree=None,
        default_topics=("apply","apply_batch","undo","redo"),
    )

    print(f"\nMy ID: {my_id}  PUB:{me['pub_port']}  SYNC:{me['sync_port']}")
    print("Peers:", ", ".join(p["id"] for p in others) or "(none)")
    _print_help()

    try:
        while True:
            try:
                line = input("> ")
            except EOFError:
                break

            parts = _clean(line)
            if not parts:
                continue

            cmd = parts[0].lower()
            # kısayollar
            if cmd in ("q", "quit", "exit"):
                break
            if cmd in ("h", "help", "?"):
                _print_help()
                continue
            if cmd in ("t", "tree"):
                print(node.pretty())
                continue
            if cmd in ("p", "pretty"):
                print(node.pretty())
                continue
            if cmd in ("u", "undo"):
                n = int(parts[1]) if len(parts) > 1 else 1
                node.undo(n)
                print("[TX] undo", n)
                continue
            if cmd in ("r", "redo"):
                n = int(parts[1]) if len(parts) > 1 else 1
                node.redo(n)
                print("[TX] redo", n)
                continue
            if cmd == "move":
                if len(parts) < 4:
                    print("kullanım: move <parent> <meta> <child>")
                    continue
                parent, meta, child = parts[1], parts[2], parts[3]
                node.apply(parent, meta, child)
                print(f"[TX] apply: parent={parent} meta={meta} child={child}")
                continue

            print("bilinmeyen komut. 'help' yazabilirsin.")
    finally:
        node.close()

if __name__ == "__main__":
    main()
