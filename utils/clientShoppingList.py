import os
import uuid
from datetime import datetime

class ShoppingList():
    def __init__(self, listId, replicaId):
        self.listId = listId
        self.replicaId = replicaId
        self.items = {"items": [], "removed": [], "acquired":[]}

    def _get_current_timestamp(self):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def _generate_item_id(self):
        return str(uuid.uuid4())

    def addItem(self, item, quantity=1):

            item_id = self._generate_item_id()
            timestamp = self._get_current_timestamp()

            for i in self.items["items"]:
                if i["name"] == item and i["acquired"] == False and i["id"] not in self.items["removed"]:

                    print(f"This Item Already Exists")
                    return

            self.items["items"].append({"id": item_id, "name": item, "quantity": quantity, "timestamp": timestamp, "acquired": False})
            print(f"Added {quantity} of {item} at {timestamp}")


    def removeItem(self, item):
            item_found = False
            for i in self.items["items"]:
                if i["name"] == item and i["acquired"] == False and i["id"] not in self.items["removed"]:
                    self.items["removed"].append(i["id"])
                    item_found = True
                    print(f"Removed {item} at {i['timestamp']}")
                    break
            if not item_found:
                print(f"{item} not found or already acquired")


    def increase(self, item, quantity=1):
            for i in self.items["items"]:
                if i["name"] == item and not i["acquired"] and i["id"] not in self.items["removed"]:
                    i["quantity"] += quantity
                    i["timestamp"] = self._get_current_timestamp()
                    print(f"Increased {item} by {quantity} to {i['quantity']}")
                    return
            print(f"{item} not found or already acquired")


    def decrease(self, item, quantity=1):
        for i in self.items["items"]:
            if i["name"] == item and not i["acquired"] and i["id"] not in self.items["removed"]:
                if i["quantity"] > quantity:
                    i["quantity"] -= quantity
                    i["timestamp"] = self._get_current_timestamp()
                    print(f"Decreased {item} by {quantity} to {i['quantity']}")
                else:
                    print(f"Cannot decrease {item} below 0")
                return
        print(f"{item} not found or already acquired")

    def acquire(self, item):
            for i in self.items["items"]:
                if i["name"] == item and i["id"] not in self.items["removed"]:
                    if i["acquired"]:
                        print(f"{item} already acquired")
                        return
                    i["acquired"] = True
                    i["timestamp"] = self._get_current_timestamp()
                    print(f"Marked {item} as acquired at {i['timestamp']}")
                    return
            print(f"{item} not found or already removed")

    def synchronize(self, server):
        print("Synchronizing with server...")

    def getListId(self):
        return self.listId

    def getReplicaId(self):
        return self.replicaId

    def showList(self):
            print("\nItems List:")
            for item in self.items["items"]:
                if item["id"] not in self.items["removed"]:
                    acquired_status = "Acquired" if item["acquired"] else "Not Acquired"
                    print(f"- {item['name']} (x{item['quantity']}) | {acquired_status}")

            """"print("\nRemoved items (IDs):")
            print(self.items["removed"])"""

    def fillFromFile(self, file_path):
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                data = file.readlines()

                for line in data[:-1]:
                    item_id, name, quantity, timestamp, acquired = line.strip().split(',')
                    self.items["items"].append({
                        "id": item_id,
                        "name": name,
                        "quantity": int(quantity),
                        "timestamp": timestamp,
                        "acquired": acquired == "True"
                    })

                if data:
                    removed_line = data[-1].strip()
                    if removed_line.startswith("Removed IDs:"):
                        removed_ids = removed_line[len("Removed IDs:"):].strip().split(",") if removed_line[len("Removed IDs:"):].strip() else []
                        self.items["removed"] = removed_ids
                    else:
                        self.items["removed"] = []

            print(f"Loaded items from {file_path}")

    def localSave(self):
        user_id = self.replicaId
        list_id = self.listId

        folder_path = os.path.join("userdata", str(user_id))
        file_path = os.path.join(folder_path, f"{list_id}.txt")

        with open(file_path, 'w') as file:
            for item in self.items["items"]:
                file.write(f"{item['id']},{item['name']},{item['quantity']},{item['timestamp']},{item['acquired']}\n")

            file.write(f"Removed IDs: {','.join(self.items['removed'])}" if self.items["removed"] else "Removed IDs:")

        print(f"Saved list to {file_path}")

