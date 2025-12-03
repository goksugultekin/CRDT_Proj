#!/usr/bin/env python3
"""
Flask web application for CRDT tree editor
Provides a web GUI for the distributed CRDT system
"""

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import threading
import time
from server_my import CRDTServer
from moveclient import MoveClient

app = Flask(__name__)
app.config['SECRET_KEY'] = 'crdt-web-app-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global server instance
crdt_server = None
clients = {}  # Store clients by session ID


def create_server():
    """Create and start the CRDT server"""
    global crdt_server
    if crdt_server is None:
        rep_port = 8000
        pub_port = 8001
        while CRDTServer is None: 
            crdt_server = CRDTServer(rep_port=rep_port, pub_port=pub_port)
            rep_port += 1
            pub_port += 1
        :
            crdt_sever


        except Exception as e:
            print(f"Error creating server: {e}")
            return None
        time.sleep(0.5)  # Give server time to start
    return crdt_server


@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    session_id = request.sid
    print(f"Client connected: {session_id}")
    
    # Create server if it doesn't exist
    create_server()
    
    # Create a client for this session
    client = MoveClient(
        server_req="tcp://127.0.0.1:5555",
        server_sub="tcp://127.0.0.1:5556",
        identity=f"web-client-{session_id[:8]}"
    )
    clients[session_id] = client
    time.sleep(0.3)
    
    # Send initial state
    try:
        pretty = client.api.pretty()
        snapshot = client.api.snapshot()
        emit('tree_update', {
            'pretty': pretty,
            'tree': snapshot.get('tree', [])
        })
    except Exception as e:
        print(f"Error sending initial state: {e}")
    
    # Set up handlers for real-time updates
    def on_applied(topic, data):
        try:
            pretty = client.api.pretty()
            snapshot = client.api.snapshot()
            socketio.emit('tree_update', {
                'pretty': pretty,
                'tree': snapshot.get('tree', []),
                'event': 'applied',
                'data': data
            }, room=session_id)
        except Exception as e:
            print(f"Error in on_applied: {e}")
    
    def on_applied_batch(topic, data):
        try:
            pretty = client.api.pretty()
            snapshot = client.api.snapshot()
            socketio.emit('tree_update', {
                'pretty': pretty,
                'tree': snapshot.get('tree', []),
                'event': 'applied_batch',
                'data': data
            }, room=session_id)
        except Exception as e:
            print(f"Error in on_applied_batch: {e}")
    
    def on_undone(topic, data):
        try:
            pretty = client.api.pretty()
            snapshot = client.api.snapshot()
            socketio.emit('tree_update', {
                'pretty': pretty,
                'tree': snapshot.get('tree', []),
                'event': 'undone',
                'data': data
            }, room=session_id)
        except Exception as e:
            print(f"Error in on_undone: {e}")
    
    def on_redone(topic, data):
        try:
            pretty = client.api.pretty()
            snapshot = client.api.snapshot()
            socketio.emit('tree_update', {
                'pretty': pretty,
                'tree': snapshot.get('tree', []),
                'event': 'redone',
                'data': data
            }, room=session_id)
        except Exception as e:
            print(f"Error in on_redone: {e}")
    
    client.on("applied", on_applied)
    client.on("applied_batch", on_applied_batch)
    client.on("undone", on_undone)
    client.on("redone", on_redone)


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    session_id = request.sid
    print(f"Client disconnected: {session_id}")
    if session_id in clients:
        try:
            clients[session_id].close()
        except:
            pass
        del clients[session_id]


@socketio.on('apply')
def handle_apply(data):
    """Handle apply operation from client"""
    session_id = request.sid
    if session_id not in clients:
        emit('error', {'message': 'Client not initialized'})
        return
    
    try:
        client = clients[session_id]
        parent = data.get('parent', '')
        meta = data.get('meta', '')
        child = data.get('child', '')
        
        if not parent or not child:
            emit('error', {'message': 'Parent and child are required'})
            return
        
        result = client.api.apply(parent, meta, child)
        emit('operation_success', {'operation': 'apply', 'result': result})
    except Exception as e:
        emit('error', {'message': str(e)})


@socketio.on('apply_batch')
def handle_apply_batch(data):
    """Handle batch apply operation from client"""
    session_id = request.sid
    if session_id not in clients:
        emit('error', {'message': 'Client not initialized'})
        return
    
    try:
        client = clients[session_id]
        moves = data.get('moves', [])
        
        if not moves:
            emit('error', {'message': 'Moves list is required'})
            return
        
        # Convert to list of tuples
        moves_tuples = [(m.get('parent'), m.get('meta', ''), m.get('child')) 
                       for m in moves]
        
        result = client.api.apply_batch(moves_tuples)
        emit('operation_success', {'operation': 'apply_batch', 'result': result})
    except Exception as e:
        emit('error', {'message': str(e)})


@socketio.on('undo')
def handle_undo(data):
    """Handle undo operation from client"""
    session_id = request.sid
    if session_id not in clients:
        emit('error', {'message': 'Client not initialized'})
        return
    
    try:
        client = clients[session_id]
        n = data.get('n', 1)
        result = client.api.undo(n)
        emit('operation_success', {'operation': 'undo', 'result': result})
    except Exception as e:
        emit('error', {'message': str(e)})


@socketio.on('redo')
def handle_redo(data):
    """Handle redo operation from client"""
    session_id = request.sid
    if session_id not in clients:
        emit('error', {'message': 'Client not initialized'})
        return
    
    try:
        client = clients[session_id]
        n = data.get('n', 1)
        result = client.api.redo(n)
        emit('operation_success', {'operation': 'redo', 'result': result})
    except Exception as e:
        emit('error', {'message': str(e)})


@socketio.on('get_tree')
def handle_get_tree():
    """Handle request for current tree state"""
    session_id = request.sid
    if session_id not in clients:
        emit('error', {'message': 'Client not initialized'})
        return
    
    try:
        client = clients[session_id]
        pretty = client.api.pretty()
        snapshot = client.api.snapshot()
        emit('tree_update', {
            'pretty': pretty,
            'tree': snapshot.get('tree', [])
        })
    except Exception as e:
        emit('error', {'message': str(e)})


if __name__ == '__main__':
    # Create server on startup
    create_server()
    
    print("\n" + "="*60)
    print("CRDT Web Application")
    print("="*60)
    print("Starting web server...")
    print("Open your browser to: http://localhost:5001")
    print("="*60 + "\n")
    
    socketio.run(app, host='0.0.0.0', port=8005, debug=True)
