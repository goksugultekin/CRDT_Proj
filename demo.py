from move_op_impl import Move, ThreadSafeState, pretty_tree, unique_parent, acyclic
from timestamper import Timestamper

ts = Timestamper()

initial_tree = {
    ("root", "", "A"),
    ("root", "", "B"),
    ("root", "", "C"),
    ("A", "", "a1"),
    ("A", "", "a2"),
    ("A", "", "a3"),
   
}
print("init___")
state = ThreadSafeState(initial_tree)

tree = state.tree()
print(pretty_tree(tree))
print("end of init___")

# -------- FIRST --------
state = ThreadSafeState(initial_tree)
print("_______ FIRST ________")
state.apply(Move(ts(), "B", "", "A"))   
state.apply(Move(ts(), "C", "", "A"))  
tree1 = state.tree()
print(pretty_tree(tree1))
print("_______ END OF FIRST ________")

# -------- SECOND --------
state2 = ThreadSafeState(tree1)
print("_______ 2ND ________")
state2.apply(Move(0, "A", "", "D"))  
state2.apply(Move(10, "C", "", "A"))  
print(pretty_tree(state2.tree()))
print("_______ END OF 2ND ________")

# -------- THIRD  --------
print("_______ 3RD ________")
state2.undo(1)                          
print(pretty_tree(state2.tree()))      
#state2.redo(1)                         
tree = state2.tree()
print(pretty_tree(tree))
print("unique_parent:", unique_parent(tree))
print("acyclic:", acyclic(tree))
print("_______ END OF 3RD ________")