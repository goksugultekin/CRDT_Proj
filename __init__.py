# CRDT Project - Conflict-free Replicated Data Types for Tree Operations
"""
A Python implementation of CRDT (Conflict-free Replicated Data Type) for tree-structured data.

This project provides:
- Move operations for tree nodes with conflict resolution
- Thread-safe state management
- Undo/redo functionality
- Timestamp-based operation ordering
- Tree validation and visualization

Main components:
- move_op_impl: Core CRDT implementation
- timestamper: Deterministic timestamp generation
- ThreadSafeState: Thread-safe state management
"""

__version__ = "0.1.0"
__author__ = "Goksu"

# Import main classes for easy access
from .move_op_impl import Move, ThreadSafeState, pretty_tree, unique_parent, acyclic
from .timestamper import Timestamper

__all__ = [
    "Move",
    "ThreadSafeState", 
    "pretty_tree",
    "unique_parent",
    "acyclic",
    "Timestamper"
]
