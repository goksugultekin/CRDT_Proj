from __future__ import annotations
import json
import sys
import time
import uuid
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
import threading
import zmq
from timestamper import *
import my_marshal 
import configGen


from move_op_impl import *




import json

# Read the config file
with open('config.json', 'r') as f:
    config = json.load(f)

if len(sys.argv) < 2:
    print(f"use: python {sys.argv[0]} <config_dosyasi.json>")
    print(f"example:   python {sys.argv[0]} config_node_A.json")
    sys.exit(1)

config_filename = sys.argv[1]

try:
    with open(config_filename, 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    print(f"error: {config_filename} not found .")
    sys.exit(1)

# my_id'yi artık config dosyasının içinden alıyoruz
my_id = config['my_id'] 
all_peers = config['peers']

my_config = next(peer for peer in all_peers if peer['id'] == my_id)

print(f"My ID: {my_config['id']}")
print(f"My IP: {my_config['ip']}")
print(f"My pub_port: {my_config['pub_port']}")
print(f"My sync_port: {my_config['sync_port']}")

other_peers = [peer for peer in all_peers if peer['id'] != my_id]

ctx = zmq.Context.instance()
lamport_clock = my_marshal.LamportClock()

#burada, operasyonları publish edeceğim pub socketini ve config. json'unu senkronize tutmak için
#tuttuğum rep socket'ini oluşturup bind'ladım.

pub_socket = ctx.socket(zmq.PUB)
pub_socket.bind(f"tcp://*:{my_config['pub_port']}")
rep_socket = ctx.socket(zmq.REP)
rep_socket.bind(f"tcp://*:{my_config['sync_port']}")

#sub socket: diğer nodelardan operasyonları alabilmem için
sub_socket = ctx.socket(zmq.SUB)




poller = zmq.Poller()

#sub ve rep socketlarım çalışıyo mu diye poll tut
poller.register(sub_socket, zmq.POLLIN)
poller.register(rep_socket, zmq.POLLIN)

crdt_state = ThreadSafeState()

def broadcast_move(parent: Any, meta: Any, child: Any):
    #bir op alıp onu yayınlıyoruz

    op = Move(
        move_time=  lamport_clock.tick(), 
        move_parent=parent,
        move_meta=meta,
        move_child=child
    )

    #önce local
    crdt_state.apply(op)

    #yayınlamak için
    op_data = asdict(op)
    op_payload = json.dumps(op_data).encode('utf-8')
    pub_socket.send_multipart([b"CRDT_OPS", op_payload])



    





def main_poller_loop():
    try:
        while True:
            socks = dict(poller.poll())

            if sub_socket in socks:
                #yeni bi iş geldiyse

                topic, op_payload = sub_socket.recv_multipart()
                try: 
                    op_data = json.loads(op_payload.decode('utf-8'))
                    op = Move(**op_data)
                    lamport_clock.update_on_receive(op.move_time)
                    crdt_state.apply(op)
                    print(f"RECEIVED OP: {op_payload.decode()}")
                    print(pretty_tree(crdt_state.tree()))

                except Exception as e:
                    print(f"error at main poller loop: {e}")



                
            if rep_socket in socks:
                #yeni bi peer katıldıysa
                message = rep_socket.recv()
                if message == b"READY":
                    # ack yolla
                    rep_socket.send(b"ACK")
                    print("Responded to new peer handshake.")

    except KeyboardInterrupt:
        print("\nShutting down...")

    finally:
        pub_socket.close()
        sub_socket.close()
        rep_socket.close()
        print("Initialization complete. Entering main loop...")
        ctx.term()





if __name__ == "__main__":
    for other_peer in other_peers:
        sub_socket.connect(f"tcp://{other_peer['ip']}:{other_peer['pub_port']}")

        sub_socket.setsockopt(zmq.SUBSCRIBE, b"CRDT_OPS")
        #tek topic, çünkü zaten göksunun logic'inden alıcam onları


        #REQ socket işleri:
        req_socket = ctx.socket(zmq.REQ)

        req_socket.connect(f"tcp://{other_peer['ip']}:{other_peer['sync_port']}")

        #READY yollayım ki senkron olalım

        req_socket.send(b"READY")
        req_socket.recv()
        req_socket.close()

    try:
        print("waiting for 5 secs for local operations")
        time.sleep(5) 
        while True:
            command_line = input("> ")
            if not command_line:
                continue
            parts = command_line.split()
            if len(parts) == 4 and parts[0].lower() == 'move':
                _, parent, meta, child = parts
                try:
                    broadcast_move(parent, meta, child)
                    time.sleep(1)
                except Exception as e:
                    print(f"error: {e}")
            elif command_line.lower() == 'tree':
                print(pretty_tree(crdt_state.tree()))
            else:
                print("didnt understand")
    except:
       print("keyboard hit. exiting. bye")

        #poller için thread
    poller_thread = threading.Thread(target=main_poller_loop, daemon=True)
    poller_thread.start()
    if poller_thread.is_alive:
        print("poller thread is doing fine. ")
    
    


    print("for new command: move <parent> <meta> <child>")
    print("example: move root init A")




    

    

    