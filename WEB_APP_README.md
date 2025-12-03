# CRDT Web Application

A beautiful web GUI for the distributed CRDT tree editor system.

## Features

- 🌳 **Visual Tree Editor**: Interactive tree structure visualization
- 🔄 **Real-time Updates**: Live synchronization using WebSockets
- 📝 **Easy Operations**: Simple forms for adding nodes and batch operations
- ↶ **Undo/Redo**: Full history support
- 🎨 **Modern UI**: Beautiful, responsive design

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Web App

Simply run:
```bash
python app.py
```

Then open your browser to: **http://localhost:5000**

## Usage

### Adding a Node

1. Enter the **Parent** node (e.g., "root")
2. Optionally enter **Metadata** (e.g., "label")
3. Enter the **Child** node (e.g., "A")
4. Click **Apply Move**

### Batch Operations

1. Click **+ Add Item** to add multiple moves
2. Fill in parent, meta, and child for each item
3. Click **Apply Batch** to apply all moves at once

### Undo/Redo

- Click **↶ Undo** to undo the last operation
- Click **↷ Redo** to redo a previously undone operation

### Tree Visualization

The tree structure is displayed in two ways:
- **Tree Structure**: Pretty-printed hierarchical view
- **Raw Tree Data**: JSON representation of the tree

## Architecture

- **Backend**: Flask with Flask-SocketIO for WebSocket support
- **Frontend**: HTML/CSS/JavaScript with Socket.IO client
- **CRDT Server**: Runs in the background, managing the distributed state
- **Real-time**: All operations are synchronized in real-time across all connected clients

## Multiple Clients

You can open multiple browser tabs/windows to see real-time collaboration:
- All clients see updates instantly
- Operations from one client appear in all others
- The tree state is synchronized across all connections

## Troubleshooting

- **Connection issues**: Make sure port 5000 is not in use
- **No updates**: Check browser console for errors
- **Server errors**: Check terminal output for detailed error messages
