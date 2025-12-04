import tkinter as tk
from tkinter import ttk
from move_op_impl import ThreadSafeState
from typing import Any, Dict, List, Tuple, Set


def build_children_map(tree: Set[Tuple[Any, Any, Any]]):
    ch: Dict[Any, List[Tuple[Any, Any]]] = {}
    for p, m, c in tree:
        ch.setdefault(p, []).append((m, c))
    return ch


def find_roots(tree: Set[Tuple[Any, Any, Any]]):
    parents = {p for (p, _, _) in tree}
    children = {c for (_, _, c) in tree}
    roots = parents - children
    return roots or parents


class CRDTGUI:
    def __init__(self, state: ThreadSafeState):
        self.state = state
        self.root = tk.Tk()
        self.root.title("CRDT Tree")
        self.root.geometry("700x500")
        self._build()
        self.refresh()
        self.root.mainloop()

    def _build(self):
        self.tree = ttk.Treeview(self.root, columns=("meta",), show="tree headings")
        self.tree.heading("#0", text="Node")
        self.tree.heading("meta", text="Edge Meta")
        self.tree.pack(fill=tk.BOTH, expand=True)

        btn = ttk.Button(self.root, text="Refresh", command=self.refresh)
        btn.pack(pady=6)

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        tree = self.state.tree()
        ch = build_children_map(tree)
        roots = sorted(find_roots(tree), key=str)

        def add(node, parent=""):
            item = self.tree.insert(parent, "end", text=str(node), values=("",))
            for m, c in sorted(ch.get(node, []), key=lambda x: str(x[1])):
                child = self.tree.insert(item, "end", text=str(c), values=(str(m),))
                add(c, item)

        for r in roots:
            add(r)


if __name__ == "__main__":
    CRDTGUI(ThreadSafeState({
        ("root", "", "A"),
        ("A", "", "a1"),
        ("A", "", "a2"),
        ("root", "", "B"),
    }))
