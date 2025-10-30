from __future__ import annotations
import json
import time
import uuid
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
import threading
import zmq
from move_op_imply import *
from timestamper import *
from my_marshal import *
from p2p_pub_sub import * 

HARDCODED_REP= "tcp://127.0.0.1:5557"
HARDCODED_REQ= "tcp://127.0.0.1:5558"


class RepReqMove:
    def __init__(self,
                 rep_addr: str = HARDCODED_REP,
                 req_addr: str = HARDCODED_SUB,
                 peer_addresses: List[str] = ["127.0.0.1"], 
                 topics: Optional[List[str]] = None,
                 ):
        
        self.ctx = zmq.Context.instance()
        self.req = self.ctx.socket(zmq.REQ)
        self.rep = self.ctx.socket(zmq.REP)
        self.req.bind(req_addr)
        self.rep.connect(rep_addr)

        self._rep_thread = threading.Thread(target=self.run_reply_server, daemon=True)
        self._rep_thread.start()
      

        self.clock = LamportClock()
        self._sub_thread = threading.Thread(target=self.subscribe, daemon=True)
        self._sub_handlers: Dict[str, List] = {t: [] for t in topics}
        self._running = True
        self._sub_thread.start()
    
    def run_reply_server(self):
        """
        This is the 'server' logic. Every peer runs this to
        answer questions from other peers.
        """
        socket = self.ctx.socket(zmq.REP)
        socket.bind(f"tcp://*:{HARDCODED_REQ_PORT}")

        while self._running:
            try:
                request = socket.recv_json()
                
                if request.get("cmd") == "snapshot":
                    # You need to implement this logic
                    data = self.get_my_current_data() 
                    socket.send_json(data)
                
                elif request.get("cmd") == "pretty":
                    # You need to implement this logic
                    text = self.get_my_pretty_string()
                    socket.send_json({"pretty": text})
                else:
                    socket.send_json({"error": "Unknown command"})
            except zmq.ZMQError:
                break # Context shutting down