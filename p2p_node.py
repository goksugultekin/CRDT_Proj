from __future__ import annotations
import json
import sys
import time
import threading
from dataclasses import asdict
from typing import Any

import zmq

from move_op_impl import Move, ThreadSafeState, pretty_tree
from my_marshal import LamportClock


def main():
    if len(sys.argv) < 2:
        print(f"usage: python {sys.argv[0]} <config_node_*.json>")
        sys.exit(1)

    with open(sys.argv[1], "r") as f:
        cfg = json.load(f)

    my_id = cfg["my_id"]
    peers = cfg["peers"]
    me = next(p for p in peers if p["id"] == my_id)
    others = [p for p in peers if p["id"] != my_id]

    print(f"My ID: {me['id']}  IP: {me['ip']}  PUB:{me['pub_port']}  SYNC:{me['sync_port']}")

    ctx = zmq.Context.instance()
    clock = LamportClock()

    # sockets
    pub = ctx.socket(zmq.PUB)
    pub.bind(f"tcp://*:{me['pub_port']}")

    rep = ctx.socket(zmq.REP)
    rep.bind(f"tcp://*:{me['sync_port']}")

    sub = ctx.socket(zmq.SUB)
    sub.setsockopt(zmq.SUBSCRIBE, b"CRDT_OPS")
    for op in others:
        sub.connect(f"tcp://{op['ip']}:{op['pub_port']}")

    # handshake
    for op in others:
        req = ctx.socket(zmq.REQ)
        req.connect(f"tcp://{op['ip']}:{op['sync_port']}")
        req.send(b"READY")
        try:
            req.recv()
        finally:
            req.close()

    poller = zmq.Poller()
    poller.register(sub, zmq.POLLIN)
    poller.register(rep, zmq.POLLIN)

    state = ThreadSafeState()

    def broadcast_move(parent: Any, meta: Any, child: Any):
        op = Move(
            move_time=clock.tick(),
            move_parent=parent,
            move_meta=meta,
            move_child=child,
        )
        state.apply(op)
        pub.send_multipart([b"CRDT_OPS", json.dumps(asdict(op)).encode("utf-8")])

    def poll_loop():
        try:
            while True:
                socks = dict(poller.poll())
                if sub in socks:
                    topic, payload = sub.recv_multipart()
                    try:
                        data = json.loads(payload.decode("utf-8"))
                        op = Move(**data)
                        clock.update_on_receive(op.move_time)
                        state.apply(op)
                        print(f"[RX] {data}")
                        print(pretty_tree(state.tree()))
                    except Exception as e:
                        print(f"poll loop decode/apply error: {e}")

                if rep in socks:
                    msg = rep.recv()
                    if msg == b"READY":
                        rep.send(b"ACK")
                    else:
                        rep.send(b"?")
        except Exception as e:
            print(f"poller stopped: {e}")

    # start background poller BEFORE CLI loop
    t = threading.Thread(target=poll_loop, daemon=True)
    t.start()

    print("ready. commands:  'move <parent> <meta> <child>'  |  'tree'")
    try:
        while True:
            line = input("> ").strip()
            if not line:
                continue
            if line == "tree":
                print(pretty_tree(state.tree()))
                continue
            parts = line.split()
            if len(parts) == 4 and parts[0].lower() == "move":
                _, parent, meta, child = parts
                try:
                    broadcast_move(parent, meta, child)
                except Exception as e:
                    print(f"error: {e}")
            else:
                print("unknown command")
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        try:
            pub.close(0)
            sub.close(0)
            rep.close(0)
        finally:
            ctx.term()


if __name__ == "__main__":
    main()
