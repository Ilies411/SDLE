import os
import uuid
from clientShoppingList import *

def create_or_load_list():
    while True:
        try:
            user_id = int(input("Welcome! Enter a user ID: "))
            fk = int(input("\n0. Work on an existing list\n1. Create a new list\n\nYour Selection: "))
            if fk == 0:
                list_id = input("Enter list ID: ")
                break
            elif fk == 1:
                list_id = str(uuid.uuid4())
                print("\nYour new list ID is:", list_id)
                break
            else:
                print("Wrong Selection")
        except ValueError:
            print("Invalid input. Try again.")
    return user_id, list_id

def manage_local_list(user_id, list_id):
    folder_path = os.path.join("userdata", str(user_id))
    file_path = os.path.join(folder_path, f"{list_id}.txt")
    os.makedirs(folder_path, exist_ok=True)

    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            print(f"\nCreated Local List: {file_path}")
            file.write("Removed IDs:")
    else:
        print(f"\nLocal List already exists: {file_path}")
    return file_path

def list_editor(shoppingList):
    while True:
        print("\nList Editor")
        try:
            key = int(input("1.Add Item\n2.Remove Item\n3.Increase Quantity\n4.Decrease Quantity\n5.Set as Acquired\n6.Synchronize\n 7.Show List\n8.Leave\nYour Selection: "))
            match key:
                case 1:
                    name = input("Enter item name: ")
                    quantity = int(input("Enter quantity: "))
                    shoppingList.addItem(name, quantity)
                case 2:
                    name = input("Enter item name to remove: ")
                    shoppingList.removeItem(name)
                case 3:
                    name = input("Enter item name to increase quantity: ")
                    quantity = int(input("Enter quantity to increase: "))
                    shoppingList.increase(name, quantity)
                case 4:
                    name = input("Enter item name to decrease quantity: ")
                    quantity = int(input("Enter quantity to decrease: "))
                    shoppingList.decrease(name, quantity)
                case 5:
                    name = input("Enter item name to set as acquired: ")
                    shoppingList.acquire(name)
                case 6:
                    shoppingList.synchronize(1)
                case 7:
                    shoppingList.showList()
                case 8:
                    break
                case _:
                    print("Invalid selection. Try again.")
        except ValueError:
            print("Invalid input. Please try again.")
        shoppingList.localSave()

def main():
    user_id, list_id = create_or_load_list()
    file_path = manage_local_list(user_id, list_id)
    shoppingList = ShoppingList(list_id, user_id)
    shoppingList.fillFromFile(file_path)

    if input("Synchronize before editing? (y/n): ").lower() == "y":
        shoppingList.synchronize(1)

    list_editor(shoppingList)

    if input("Synchronize before leaving? (y/n): ").lower() == "y":
        shoppingList.synchronize(1)

    print("Goodbye!")

if __name__ == "__main__":
    main()








