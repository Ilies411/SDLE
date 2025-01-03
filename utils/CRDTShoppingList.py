import uuid
from utils.pncounter import PNCounter
import os
from secrets import token_urlsafe
import random

class ShoppingList:
    def __init__(self):
        print("HELLLO")
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

    def fill_with_item(self, item_id, item):
        # Add item to the shopping map
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
            return
        # Add item to the shopping map
        else:
            self.shopping_map[item_id] = {
            "name": item["name"],
            "quantity": quantity_counter.query(),
            "acquired": acquired_counter.query(),
            "timestamp": timestamp
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
                # Apenas atualiza o status para True, sem incrementar a quantidade
                acquired_counter.inc(item_id)  # Isso pode ser removido se não for necessário
                self.shopping_map[item_id]["acquired"] = True  # Atualiza para True
            else:
                acquired_counter.dec(item_id)
                self.shopping_map[item_id]["acquired"] = False  # Atualiza para False
            self.shopping_map[item_id]["timestamp"] = timestamp
            return timestamp

    def fillFromFile(self, file_path):
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                data = file.readlines()
                for line in data[1:]:
                    item_id, name, quantity, timestamp, acquired = line.strip().split(',')
                    self.fill_with_item(item_id, {
                        "name": name,
                        "quantity": int(quantity),
                        "timestamp": int(timestamp),
                        "acquired": acquired == "True" or acquired == '1'
                    })
                main_parts = data[0].split("_", 2)
                self.replica_id = int(main_parts[0])
                self.id = main_parts[1]
                remaining = main_parts[2]
                remaining = remaining.replace("\n", "", 1)
                dict_end = remaining.find("}") + 1
                self.v = eval(remaining[:dict_end])
                print(self.v)

    def localSave(self, type="userdata"):
        folder_path = os.path.join(type, str(self.replica_id))
        file_path = os.path.join(folder_path, f"{self.id}.txt")
        os.makedirs(folder_path, exist_ok=True)

        with open(file_path, 'w') as file:
            file.write(f"{self.replica_id}_{self.id}_{self.v}_\n")
            for item_id, item in self.shopping_map.items():
                file.write(f"{item_id},{item['name']},{item['quantity']},{item['timestamp']},{str(item['acquired'])}\n")

        print(f"Saved list to {file_path}")

    def show_list(self):
        print("\nShopping List:")
        for item_id, item in self.shopping_map.items():
            status = "Acquired" if item["acquired"] else "Not Acquired"
            print(f"- {item['name']} (x{item['quantity']}) | {status}")

    def merge(self, replica):
        print("[debug]merge")
        print("d",replica.v)
        print("d",self.v)
        # Verifica se a lista local está vazia
        if not self.shopping_map:
            # Se a lista local estiver vazia, simplesmente copia a lista da réplica
            self.shopping_map = replica.shopping_map.copy()
            self.quantity_counters = replica.quantity_counters.copy()
            self.acquired_counters = replica.acquired_counters.copy()
            self.v = replica.v.copy()
            return self

        # Verifica se a lista da réplica está vazia
        if not replica.shopping_map and not replica.v:
            # Se a lista da réplica estiver vazia, não faz nada
            return self

        # Extraindo nomes dos itens da instância atual e da réplica
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
                if replica_id in replica_v and self.replica_id in local_v:
                    if replica_v[replica.replica_id] > local_v[self.replica_id]:
                        # Check for conflicts in acquired status
                        if replica_item["acquired"] != self_item["acquired"]:
                            # Criar cópias separadas para itens adquiridos e não adquiridos
                            new_item_id = f"{item_name}_acquired"
                            self.shopping_map[new_item_id] = {
                                "name": item_name,
                                "quantity": self_item["quantity"],
                                "acquired": True,
                                "timestamp": self_item["timestamp"]
                            }
                            new_item_id_not_acquired = f"{item_name}_not_acquired"
                            self.shopping_map[new_item_id_not_acquired] = {
                                "name": item_name,
                                "quantity": replica_item["quantity"],
                                "acquired": False,
                                "timestamp": replica_item["timestamp"]
                            }
                        # Check for conflicts in quantities
                        if replica_item["quantity"] != self_item["quantity"]:
                            # Prioriza a maior quantidade
                            self.shopping_map[self_id]["quantity"] = max(self_item["quantity"], replica_item["quantity"])
                            self.shopping_map[self_id]["timestamp"] = max(self_item["timestamp"], replica_item["timestamp"])
                            
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
                print("HHHHH",item_name)
                print(replica_v)
                print(local_v)
                item_id = self.get_item_id_by_name(item_name)
                if item_id is not None:
                    if all(key in replica_v for key in local_v):
                        if all(key == self.replica_id and (local_v[key] <= replica_v[key] + 1) or key != self.replica_id and replica_v[key] >= local_v[key] for key in local_v):
                            del self.shopping_map[item_id]

        # Mesclar contadores de quantidade e status de aquisição
        for item_id in replica.quantity_counters:
            corresponding_item_id = None
            for existing_id, item in self.shopping_map.items():
                if item['name'] == replica.shopping_map[item_id]['name']:
                    corresponding_item_id = existing_id
                    break
            
            if corresponding_item_id is None:
                corresponding_item_id = item_id

            if corresponding_item_id not in self.quantity_counters:
                self.quantity_counters[corresponding_item_id] = PNCounter(replica.replica_id, corresponding_item_id)
                self.quantity_counters[corresponding_item_id].add_new_node(corresponding_item_id)
            
            self.quantity_counters[corresponding_item_id].merge(replica.quantity_counters[item_id])
            
            if corresponding_item_id in self.shopping_map:
                self.shopping_map[corresponding_item_id]["quantity"] = self.quantity_counters[corresponding_item_id].query()
        # Atualiza a quantidade usando o quantity counter

        for item_id in replica.acquired_counters:
            if item_id not in self.acquired_counters:
                self.acquired_counters[item_id] = PNCounter(replica.replica_id, item_id)
            self.acquired_counters[item_id].merge(replica.acquired_counters[item_id])
        for item_id in self.acquired_counters:
            if item_id in self.shopping_map:
                self.shopping_map[item_id]["acquired"] = self.acquired_counters[item_id].query()
        
        
        for replica_id in replica_v:
            if replica_id in local_v:
                local_v[replica_id] = max(local_v[replica_id], replica_v[replica_id])
            else:
                local_v[replica_id] = replica_v[replica_id]
        print("ahdu")
        return self
