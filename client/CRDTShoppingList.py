import uuid
from .pncounter import PNCounter
from secrets import token_urlsafe
import random

class ShoppingList:
    def __init__(self):
        self.id = 0  # =token_urlsafe(16)
        self.replica_id = 0
        self.v = {}  # vector clock to track the causal ordering of operations
        self.shopping_map = {}  # key, value: itemID, item attributes (id, name, quantity, acquired, timestamp)
        self.Users = set()
        self.quantity_counters = {}
        self.acquired_counters = {}

    def set_vector_clock(self, dict):
        self.v = dict

    def get_vector_clock(self):
        return self.v

    def set_replica_id(self, replica_id):
        self.replica_id = replica_id

    def my_replica_id(self):
        """Returns the ID of the shopping list."""
        return self.replica_id

    def set_id(self, id):
        self.id = id

    def my_id(self):
        """Returns the ID of the shopping list."""
        return self.id

    def is_empty(self):
        """Returns True if shopping list is empty, or False otherwise"""
        return self.shopping_map == {}

    def delete_list(self, id):
        """Deletes the shopping list identified by the provided list_id."""
        if id == self.id:
            # Clear all the attributes related to the shopping list
            self.name = ""
            self.shopping_map = {}
            self.Users = set()
            self.quantity_counters = {}
            self.acquired_counters = {}
            self.v = {}
            print(f"Shopping list with ID '{id}' has been deleted.")
        else:
            print("Invalid list ID. Deletion failed.")

    def associate_user(self, user_id):
        """
        Associate a user with the shopping list.
        Adds user id to shopping list's Users set
        """
        self.Users.add(user_id)

    def contains(self, item_id):
        """Checks if the item is present in the shopping list."""
        return item_id in self.shopping_map

    def get_shopping_list(self, id=None):
        """Returns the shopping list's name, ID, and items."""
        if id is None or id != self.id:
            raise ValueError("Invalid Shopping List ID or no ID provided.")
        shopping_list_info = {
            "list_id": self.id,
            "items": self.shopping_map
        }
        return shopping_list_info

    # add_item but with concrete values from acquired and timestamp
    def fill_with_item(self, item_id, item):
        # Add item to the shopping map
        # item_id = str(uuid.uuid4()) 
        quantity_counter = PNCounter(self.replica_id, item_id)
        acquired_counter = PNCounter(self.replica_id, item_id)
        quantity_counter.add_new_node(item_id)
        acquired_counter.add_new_node(item_id)
        quantity_counter.inc(item_id, int(item["quantity"]))
        if item["acquired"]:
            acquired_counter.inc(item_id)

        self.shopping_map[item_id] = {
            "name": item["name"],
            "quantity": item["quantity"],
            "acquired": item["acquired"],
            "timestamp": item["timestamp"]
        }
        self.quantity_counters[item_id] = quantity_counter
        self.acquired_counters[item_id] = acquired_counter
        self.v[self.replica_id] = int(item["timestamp"])

    def add_item(self, item_id, item):
        """
        Adds an item to the shopping list.
        Parameters:
        - item_id: Item ID
        - item: Dictionary containing item attributes
        """
        timestamp = self.increment_counter()
        quantity_counter = PNCounter(self.replica_id, item_id)
        acquired_counter = PNCounter(self.replica_id, item_id)
        quantity_counter.add_new_node(item_id)
        acquired_counter.add_new_node(item_id)
        quantity_counter.inc(item_id, item["quantity"])
        self.quantity_counters[item_id] = quantity_counter
        self.acquired_counters[item_id] = acquired_counter
        item_name = item['name']
        existing_items = [existing_item for existing_item in self.shopping_map.values() if existing_item["name"] == item_name]
        if existing_items:
            print(f"Warning! An item with the name '{item_name}' already exists in this shopping list.")
            print(quantity_counter.query())
        # Add item to the shopping map
        self.shopping_map[item_id] = {
            "name": item["name"],
            "quantity": quantity_counter.query(),
            "acquired": acquired_counter.query(),
            "timestamp": timestamp  # ver este timestamp
        }
        return timestamp

    def remove_item(self, item_name):
        """
        Removes an item of the shopping list.
        Parameters:
        - item_name: Name of item to remove
        """
        item_id = self.get_item_id_by_name(item_name)
        if item_id not in self.shopping_map:
            raise ValueError("Item ID does not exist in the shopping list.")

        if item_id in self.shopping_map:
            timestamp = self.increment_counter()
            del self.shopping_map[item_id]
            del self.quantity_counters[item_id]
            del self.acquired_counters[item_id]
            return timestamp

    def increment_counter(self):
        if self.replica_id not in self.v:
            self.v[self.replica_id] = 1
        else:
            self.v[self.replica_id] += 1
        return self.v[self.replica_id]

    def get_item_id_by_name(self, item_name):
        """
        Returns the item ID of the item with the provided name.
        """
        for item_id, item in self.shopping_map.items():
            if item["name"] == item_name:
                return item_id
        return None

    def get_quantity_counter(self, item_id):
        """
        Returns the quantity counter of the item with the provided ID.
        """
        return self.quantity_counters[item_id]

    def increment_quantity(self, item_id):
        """
        Increments the quantity of the shopping list item
        """
        if item_id in self.shopping_map:
            # Generate the vector clock timestamp for the increment operation
            timestamp = self.increment_counter()
            quantity_counter = self.quantity_counters[item_id]
            quantity_counter.inc(item_id, 1)
            self.shopping_map[item_id]["quantity"] = quantity_counter.query()
            self.shopping_map[item_id]["timestamp"] = timestamp
            print("Increment quantity")
            print(self.shopping_map[item_id]["timestamp"])
            return timestamp

    def decrement_quantity(self, item_id):
        """
        Decrements the quantity of the shopping list item
        """
        if item_id in self.shopping_map and self.shopping_map[item_id]["quantity"] > 0:
            if int(self.shopping_map[item_id]["quantity"]) <= 1:
                raise ValueError("Item quantity cannot be negative or zero.")
            else:
                # Generate the vector clock timestamp for the decrement operation
                timestamp = self.increment_counter()
                quantity_counter = self.quantity_counters[item_id]
                quantity_counter.dec(item_id)
                self.shopping_map[item_id]["quantity"] = quantity_counter.query()
                self.shopping_map[item_id]["timestamp"] = timestamp
                return timestamp

    def update_acquired_status(self, item_id, status):
        """
        Sets the item as acquired or not acquired
        """
        if item_id in self.shopping_map:
            timestamp = self.increment_counter()
            acquired_counter = self.acquired_counters[item_id]
            if status:
                acquired_counter.inc(item_id)
                self.shopping_map[item_id]["acquired"] = acquired_counter.query()
            else:
                acquired_counter.dec(item_id)
                self.shopping_map[item_id]["acquired"] = acquired_counter.query()
            self.shopping_map[item_id]["timestamp"] = timestamp
            return timestamp

    def merge(self, replica):
        # Extract item names from the current instance and the replica
        self_items_names = {item['name']: item for item in self.shopping_map.values()}
        replica_items_names = {item['name']: item for item in replica.shopping_map.values()}
        local_v = self.v
        replica_v = replica.v

        # Handle conflicts based on timestamps, quantities and acquired status
        for item_name in replica_items_names:
            is_self_defined = False
            for item_id, item in self.shopping_map.items():
                if item_name == item['name']:
                    self_id = item_id
                    self_item = item
                    is_self_defined = True
            for item_id, item in replica.shopping_map.items():
                if item_name == item['name']:
                    replica_id = item_id
                    replica_item = item
            if is_self_defined:
                # If replica's modification is more recent
                if replica_v[replica.replica_id] > local_v[self.replica_id]:
                    # Check for conflicts in acquired status
                    if replica_item["acquired"] != self_item["acquired"]:
                        self.shopping_map[self_id]["acquired"] = replica_item["acquired"]
                        self.shopping_map[self_id]["timestamp"] = replica_item["timestamp"]

                    # Check for conflicts in quantities
                    if replica_item["quantity"] != self_item["quantity"]:
                        self.shopping_map[self_id]["quantity"] = int(replica_item["quantity"])
                        self.shopping_map[self_id]["timestamp"] = replica_item["timestamp"]
                else:
                    self.shopping_map[self_id] = replica_item
            else:
                self.shopping_map[replica_id] = replica_item

        # Merge items from replica into self.shopping_map
        for item_name in replica_items_names:
            if item_name not in self_items_names:
                for item_id, item in replica.shopping_map.items():
                    if item_name == item['name']:
                        self.shopping_map[item_id] = item

        # Mesclar itens da réplica na instância atual
        for item_name in self_items_names:
            if item_name not in replica_items_names:
                item_id = self.get_item_id_by_name(item_name)
                if item_id is not None:
                    if replica_v[replica.replica_id] > local_v[self.replica_id]:
                        del self.shopping_map[item_id]

        # Mesclar contadores de quantidade e status de aquisição
        for item_id in replica.quantity_counters:
            if item_id not in self.quantity_counters:
                self.quantity_counters[item_id] = PNCounter(replica.replica_id, item_id)
            self.quantity_counters[item_id].merge(replica.quantity_counters[item_id])

        for item_id in replica.acquired_counters:
            if item_id not in self.acquired_counters:
                self.acquired_counters[item_id] = PNCounter(replica.replica_id, item_id)
            self.acquired_counters[item_id].merge(replica.acquired_counters[item_id])

        return self
