# server_my.py
# ZeroMQ-based CRDT server for distributed operations

from __future__ import annotations
import json
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple
import zmq
from move_op_impl import Move, ThreadSafeState, pretty_tree
from my_marshal import move_from_dict, logmove_to_dict, tree_to_list


class CRDTServer:
    """
    CRDT Server - ZeroMQ-based server for distributed CRDT operations
    
    This class:
    1. Listens for requests from clients
    2. Applies CRDT operations
    3. Broadcasts updates to all clients
    """
    
    def __init__(self, rep_port: int = 5555, pub_port: int = 5556):
        """
        Initialize CRDT server
        
        Args:
            rep_port: Port for receiving client requests
            pub_port: Port for broadcasting updates
        """
        print("Starting CRDT Server...")
        
        # Create ZeroMQ context
        self.ctx = zmq.Context.instance()
        
        # REP socket for receiving client requests
        self.rep = self.ctx.socket(zmq.REP)
        self.rep.bind(f"tcp://*:{rep_port}")
        print(f"  REP socket: tcp://*:{rep_port}")
        
        # PUB socket for broadcasting updates
        self.pub = self.ctx.socket(zmq.PUB)
        self.pub.bind(f"tcp://*:{pub_port}")
        print(f"  PUB socket: tcp://*:{pub_port}")
        
        # Initialize CRDT state
        initial_tree = {("root", "", "A"), ("root", "", "B")}
        self.state = ThreadSafeState(initial_tree)
        print(f"  Initial tree: {len(initial_tree)} nodes")
        
        # Start server thread
        self._running = True
        self._server_thread = threading.Thread(target=self._handle_requests, daemon=True)
        self._server_thread.start()
        
        print("CRDT Server started successfully!")

    def _handle_requests(self):
        """
        Handle requests from clients
        This function runs continuously and waits for requests
        """
        print("Request handler started...")
        
        while self._running:
            try:
                # Receive request from client
                request = self.rep.recv_json()
                
                # Process the request
                response = self._process_request(request)
                
                # Send response to client
                self.rep.send_json(response)
                
            except zmq.ZMQError as e:
                if self._running:  # Only print unexpected errors
                    print(f"  ZMQ error: {e}")
                break
            except Exception as e:
                print(f"  Error: {e}")
                error_response = {"ok": False, "error": str(e)}
                try:
                    self.rep.send_json(error_response)
                except:
                    pass

    def _process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process client request and return response
        
        Args:
            request: Request from client
            
        Returns:
            Server response
        """
        cmd = request.get("cmd")
        
        try:
            if cmd == "apply":
                return self._handle_apply(request)
            elif cmd == "apply_batch":
                return self._handle_apply_batch(request)
            elif cmd == "undo":
                return self._handle_undo(request)
            elif cmd == "redo":
                return self._handle_redo(request)
            elif cmd == "snapshot":
                return self._handle_snapshot(request)
            elif cmd == "pretty":
                return self._handle_pretty(request)
            else:
                return {"ok": False, "error": f"Unknown command: {cmd}"}
                
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _handle_apply(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply single move operation
        
        Args:
            request: {"cmd": "apply", "move": {...}}
            
        Returns:
            {"ok": True, "log": [...], "tree": [...]}
        """
        # Create Move object
        move_data = request["move"]
        move = move_from_dict(move_data)
        
        # Apply operation
        self.state.apply(move)
        
        # Get current state
        log = self.state.log()
        tree = self.state.tree()
        
        # Broadcast to all clients
        self._broadcast("applied", {
            "move": move_data,
            "log": [logmove_to_dict(l) for l in log],
            "tree": tree_to_list(tree)
        })
        
        return {
            "ok": True,
            "log": [logmove_to_dict(l) for l in log],
            "tree": tree_to_list(tree)
        }

    def _handle_apply_batch(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply batch move operations
        
        Args:
            request: {"cmd": "apply_batch", "moves": [...]}
            
        Returns:
            {"ok": True, "log": [...], "tree": [...]}
        """
        # Create Move objects
        moves_data = request["moves"]
        moves = [move_from_dict(m) for m in moves_data]
        
        # Apply all operations
        for move in moves:
            self.state.apply(move)
        
        # Get current state
        log = self.state.log()
        tree = self.state.tree()
        
        # Broadcast to all clients
        self._broadcast("applied_batch", {
            "moves": moves_data,
            "log": [logmove_to_dict(l) for l in log],
            "tree": tree_to_list(tree)
        })
        
        return {
            "ok": True,
            "log": [logmove_to_dict(l) for l in log],
            "tree": tree_to_list(tree)
        }

    def _handle_undo(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply undo operation
        
        Args:
            request: {"cmd": "undo", "n": 1}
            
        Returns:
            {"ok": True, "log": [...], "tree": [...]}
        """
        n = request.get("n", 1)
        
        # Apply undo
        self.state.undo(n)
        
        # Get current state
        log = self.state.log()
        tree = self.state.tree()
        
        # Broadcast to all clients
        self._broadcast("undone", {
            "n": n,
            "log": [logmove_to_dict(l) for l in log],
            "tree": tree_to_list(tree)
        })
        
        return {
            "ok": True,
            "log": [logmove_to_dict(l) for l in log],
            "tree": tree_to_list(tree)
        }

    def _handle_redo(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply redo operation
        
        Args:
            request: {"cmd": "redo", "n": 1}
            
        Returns:
            {"ok": True, "log": [...], "tree": [...]}
        """
        n = request.get("n", 1)
        
        # Apply redo
        self.state.redo(n)
        
        # Get current state
        log = self.state.log()
        tree = self.state.tree()
        
        # Broadcast to all clients
        self._broadcast("redone", {
            "n": n,
            "log": [logmove_to_dict(l) for l in log],
            "tree": tree_to_list(tree)
        })
        
        return {
            "ok": True,
            "log": [logmove_to_dict(l) for l in log],
            "tree": tree_to_list(tree)
        }

    def _handle_snapshot(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get current tree snapshot
        
        Args:
            request: {"cmd": "snapshot"}
            
        Returns:
            {"ok": True, "tree": [...]}
        """
        tree = self.state.tree()
        return {
            "ok": True,
            "tree": tree_to_list(tree)
        }

    def _handle_pretty(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get pretty-formatted tree
        
        Args:
            request: {"cmd": "pretty"}
            
        Returns:
            {"ok": True, "pretty": "..."}
        """
        tree = self.state.tree()
        pretty_str = pretty_tree(tree)
        return {
            "ok": True,
            "pretty": pretty_str
        }

    def _broadcast(self, topic: str, data: Dict[str, Any]):
        """
        Broadcast update to all clients
        
        Args:
            topic: Broadcast topic (applied, undone, etc.)
            data: Data to broadcast
        """
        try:
            message = json.dumps(data)
            self.pub.send_multipart([topic.encode("utf-8"), message.encode("utf-8")])
        except Exception:
            pass

    def close(self):
        """
        Close server and clean up resources
        """
        self._running = False
        try:
            self.rep.close(0)
            self.pub.close(0)
        except Exception:
            pass


def logmove_to_dict(lm) -> Dict[str, Any]:
    """Convert LogMove object to dictionary"""
    return {
        "log_time": lm.log_time,
        "old_parent": lm.old_parent,
        "new_parent": lm.new_parent,
        "log_meta": lm.log_meta,
        "log_child": lm.log_child,
    }