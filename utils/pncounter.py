<<<<<<<< HEAD:crdt/pncounter.py
from crdt.gcounter import GCounter
========
from utils.gcounter import GCounter
>>>>>>>> 6caae548f98c7924aceef6ca5fec02b22c3d36de:utils/pncounter.py

class PNCounter:
    def __init__(self, replica_id, item_id):
        self.P = GCounter(item_id, replica_id)
        self.N = GCounter(item_id, replica_id)
        self.item_id = item_id
        self.replica_id = replica_id

    def add_new_node(self, item_id):
        self.P.add_new_node(item_id)
        self.N.add_new_node(item_id)

    def inc(self, item_id, quantity=1):
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        elif quantity > 1:
            for i in range(quantity):
                self.P.inc(item_id)
        else:
            self.P.inc(item_id)

    def dec(self, item_id):
         self.N.inc(item_id)

    def query(self):
        return self.P.query() - self.N.query()

    def compare(self, pnc2):
        return self.P.compare(pnc2.P) and self.N.compare(pnc2.N)

    def merge(self, pnc2):
        self.P.merge(pnc2.P)
        self.N.merge(pnc2.N)

    def display(self, name):
        # Display object P
        print("{}.P: ".format(name), end="")
        self.P.display()

        # Display object N
        print("{}.N: ".format(name), end="")
        self.N.display()