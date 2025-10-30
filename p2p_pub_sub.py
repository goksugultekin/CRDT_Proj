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

HARDCODED_PUB= "tcp://127.0.0.1:5555"
HARDCODED_SUB= "tcp://127.0.0.1:5556"

class PubSubMove:

    """
    - pub/sub socketleri ile revize ettim. 
    - asenkron broadcast ile, eventual consistency
    -öncelikle op-based. böylece sadece tüm operasyonlar pass edilerek overhead düşürülecek
    
    bu classın amacı: pub sub kullanarak tüm nodelara, cevap beklemeden move'ları tebliğ etmek. onun dışında bir şey yapmıyor. 

    ilk kopya için portlar 5555 ve 5556. 
    """
    def __init__(self,
                 pub_addr: str = HARDCODED_PUB,
                 sub_addr: str = HARDCODED_SUB,
                 topics: Optional[List[str]] = None,
                 ):
        self.state = ThreadSafeState()
        self.ctx = zmq.Context.instance()
        self.pub = self.ctx.socket(zmq.PUB)
        #self.pub.setsockopt() 
        self.pub.bind(pub_addr)
        #BURAYA KADAR PUBLISHING.
        self._wire_default_handlers()
        time.sleep(0.2)





        self.sub = self.ctx.socket(zmq.SUB)
        self.sub.connect(sub_addr)
        if not topics:
            topics = ["apply", "apply_batch", "undo", "redo"]
        for t in topics:
            self.sub.setsockopt_string(zmq.SUBSCRIBE, t)

        self.clock = LamportClock()
        self._sub_thread = threading.Thread(target=self.subscribe, daemon=True)
        self._sub_handlers: Dict[str, List] = {t: [] for t in topics}
        self._running = True
        self._sub_thread.start()

    def on(self, topic: str, handler):
        self._sub_handlers.setdefault(topic, []).append(handler)

    def subscribe(self):
        while self._running:
            try:
                topic, payload = self.sub.recv_multipart(flags=0)
                topic = topic.decode("utf-8")
                data = json.loads(payload.decode("utf-8"))
                msg_time = data.get("move", {}).get("move_time")
                if not msg_time and "moves" in data:
                     msg_time = max(m.get("move_time", 0) for m in data["moves"])
                
                if msg_time:
                    self.clock.update_on_receive(int(msg_time))

                for h in self._sub_handlers.get(topic, []):
                    try:
                        h(topic, data)
                    except Exception:
                        pass

            except zmq.ZMQError:
                break

    def _send(self, topic: str, payload: Dict[str, Any]):
        self.pub.send_multipart([topic.encode("utf-8"),json.dumps(to_jsonable(payload)).encode("utf-8")])
         
    
   
       
    def apply(self, move_parent, move_meta, move_child, move_time=None):
    
       
        move_time = self.clock.tick()
        self._send("apply", {"move": {"move_time": move_time, "move_parent": move_parent,"move_meta": move_meta, "move_child": move_child}})

    def apply_batch(self, moves):
        batch = [{"move_time": self.clock.tick(),
                "move_parent": p, "move_meta": m, "move_child": c}
                for (p, m, c) in moves]
        self._send("apply_batch", {"moves": batch})

    def undo(self, n: int = 1):
        self._send("undo", {"n": n})

    def redo(self, n: int = 1):
        self._send("redo", {"n": n})


    def _wire_default_handlers(self):
        def _h_apply(_topic, data):
            mv = data["move"]
            # Lamport merge
            self.clock.update_on_receive(int(mv.get("move_time", 0)))
            self.state.apply(Move(
                mv["move_time"], mv["move_parent"], mv["move_meta"], mv["move_child"]
            ))

        def _h_apply_batch(_topic, data):
            moves = data["moves"]
            for mv in moves:
                self.clock.update_on_receive(int(mv.get("move_time", 0)))
                self.state.apply(Move(
                    mv["move_time"], mv["move_parent"], mv["move_meta"], mv["move_child"]
                ))

        def _h_undo(_topic, data):
            self.state.undo(int(data.get("n", 1)))

        def _h_redo(_topic, data):
            self.state.redo(int(data.get("n", 1)))

        self.on("apply", _h_apply)
        self.on("apply_batch", _h_apply_batch)
        self.on("undo", _h_undo)
        self.on("redo", _h_redo)
        
  
              

    def close(self):
            self._running = False
            try:
                self.sub.close(0)
                self.pub.close(0)
                print(pretty_tree(self.state.tree()))
                
            finally:
                pass 