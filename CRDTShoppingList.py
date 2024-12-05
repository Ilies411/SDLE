
import os
import uuid
from datetime import datetime

class ShoppingList():
    def __init__(self, listId=None, replicaId=None):
        self.listId = listId or str(uuid.uuid4())
        self.replicaId = replicaId or str(uuid.uuid4())
        self.items = {}
        self.removed_items = set()
        self.vector_clock = {}

    def add_item(self, item_id, item_data):
        if item_id in self.removed_items:
            print(f"Item {item_data['name']} was removed and cannot be re-added directly.")
            return

        if item_id in self.items:
            print(f"Item {item_data['name']} already exists. Updating quantity and timestamp.")
            self.items[item_id]['quantity'] += item_data['quantity']
            self.items[item_id]['timestamp'] = item_data['timestamp']
        else:
            self.items[item_id] = item_data
            print(f"Added item {item_data['name']} with quantity {item_data['quantity']}.")

    def remove_item(self, item_id):
        if item_id in self.items:
            self.removed_items.add(item_id)
            del self.items[item_id]
            print(f"Removed item with ID {item_id}.")
        else:
            print(f"Item ID {item_id} not found.")

    def update_vector_clock(self, replica_id):
        self.vector_clock[replica_id] = self.vector_clock.get(replica_id, 0) + 1

    def get_vector_clock(self):
        return self.vector_clock

    def set_vector_clock(self, new_clock):
        self.vector_clock = new_clock

    def merge(self, other_list):
        # Merge vector clocks
        for replica, counter in other_list.get_vector_clock().items():
            self.vector_clock[replica] = max(self.vector_clock.get(replica, 0), counter)

        # Merge items
        for item_id, item_data in other_list.items.items():
            if item_id in self.removed_items:
                continue

            if item_id not in self.items:
                self.add_item(item_id, item_data)
            else:
                current_item = self.items[item_id]
                if item_data['timestamp'] > current_item['timestamp']:
                    self.items[item_id] = item_data

        # Merge removed items
        self.removed_items.update(other_list.removed_items)

    def get_shopping_list(self):
        return self.items

    def my_id(self):
        return self.listId

    def my_replica_id(self):
        return self.replicaId


class CRDTShoppingListMerger:
    def __init__(self):
        pass

    def merge_shopping_lists(self, list1, list2):
        merged_list = ShoppingList(listId=list1.my_id(), replicaId=list1.my_replica_id())
        merged_list.set_vector_clock({
            **list1.get_vector_clock(),
            **list2.get_vector_clock(),
        })

        merged_list.merge(list2)
        print("Merge completed successfully.")
        return merged_list


# Exemplo de uso:
if __name__ == "__main__":
    shopping_list1 = ShoppingList()
    shopping_list2 = ShoppingList()

    shopping_list1.add_item(str(uuid.uuid4()), {"name": "Banana", "quantity": 3, "acquired": False, "timestamp": "2024-12-04"})
    shopping_list2.add_item(str(uuid.uuid4()), {"name": "Apple", "quantity": 5, "acquired": True, "timestamp": "2024-12-03"})

    merger = CRDTShoppingListMerger()
    merged_list = merger.merge_shopping_lists(shopping_list1, shopping_list2)

    print("Merged Shopping List:")
    print(merged_list.get_shopping_list())
