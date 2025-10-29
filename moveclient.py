# moveclient.py
# ZeroMQ-based CRDT client for distributed operations

from __future__ import annotations
import json
import threading
import time
import uuid
from typing import Any, Dict, List, Optional
import zmq
from my_marshal import to_jsonable
from clientapi import ClientAPI


class LamportClock:
    """Lamport logical clock for distributed systems"""
    
    def __init__(self, initial: int = 0):
        self._lock = threading.Lock()
        self._t = int(initial)

    def now(self) -> int:
        """Get current timestamp"""
        with self._lock:
            return self._t

    def tick(self) -> int:
        """Increment and return timestamp"""
        with self._lock:
            self._t += 1
            return self._t

    def update_on_receive(self, received_ts: int) -> int:
        """Update clock when receiving message from another process"""
        with self._lock:
            self._t = max(self._t, int(received_ts)) + 1
            return self._t


class MoveClient:
    """
    ZeroMQ-based CRDT client for distributed operations
    - REQ socket to send commands to server
    - SUB socket to listen for broadcasts
    Client also keeps a Lamport clock (merged with server on replies).
    """
    
    def __init__(self,
                 server_req: str = "tcp://127.0.0.1:5555",
                 server_sub: str = "tcp://127.0.0.1:5556",
                 topics: Optional[List[str]] = None,
                 identity: Optional[str] = None):
        
        self.ctx = zmq.Context.instance()
        
        # REQ socket for sending commands
        self.req = self.ctx.socket(zmq.REQ)
        if identity is None:
            identity = f"client-{uuid.uuid4().hex[:8]}"
        self.req.setsockopt(zmq.IDENTITY, identity.encode("utf-8"))
        self.req.connect(server_req)

        # SUB socket for receiving broadcasts
        self.sub = self.ctx.socket(zmq.SUB)
        self.sub.connect(server_sub)
        if not topics:
            topics = ["applied", "applied_batch", "undone", "redone"]
        for t in topics:
            self.sub.setsockopt_string(zmq.SUBSCRIBE, t)

        # Initialize clock and handlers
        self.clock = LamportClock()
        self._sub_thread = threading.Thread(target=self._listen_broadcasts, daemon=True)
        self._sub_handlers: Dict[str, List] = {t: [] for t in topics}
        self._running = True
        self._sub_thread.start()
        
        # Initialize API
        self.api = ClientAPI(self)

    def on(self, topic: str, handler):
        """Register handler for specific topic"""
        self._sub_handlers.setdefault(topic, []).append(handler)

    def _listen_broadcasts(self):
        """Listen for broadcast messages from server"""
        while self._running:
            try:
                topic, payload = self.sub.recv_multipart(flags=0)
                topic = topic.decode("utf-8")
                data = json.loads(payload.decode("utf-8"))
                
                # Call registered handlers
                for h in self._sub_handlers.get(topic, []):
                    try:
                        h(topic, data)
                    except Exception:
                        pass
            except zmq.ZMQError:
                break

    def _send(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Send message to server and get response"""
        self.req.send_json(to_jsonable(msg))
        resp = self.req.recv_json()
        if not resp.get("ok", False):
            raise RuntimeError(resp.get("error", "unknown error"))
        return resp

    def close(self):
        """Close client connections"""
        self._running = False
        try:
            self.sub.close(0)
            self.req.close(0)
        finally:
            pass
