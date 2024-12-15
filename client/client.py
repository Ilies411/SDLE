import sys
from pathlib import Path

# Adiciona o diretório raiz do projeto ao PYTHONPATH
sys.path.append(str(Path(__file__).resolve().parent.parent))

from flask import Flask, request, redirect, url_for, render_template, jsonify
import os
import uuid
from utils.CRDTShoppingList import *
import zmq

app = Flask(__name__)

shopping_lists = {}

def load_existing_lists(user_id):
    folder_path = os.path.join("userdata", str(user_id))
    if not os.path.exists(folder_path):
        return []

    return [file.split('.')[0] for file in os.listdir(folder_path) if file.endswith(".txt")]

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        user_id = request.form["user_id"]
        action = request.form["action"]

        if action == "new":
            list_id = str(uuid.uuid4())
            return redirect(url_for("shopping_list", user_id=user_id, list_id=list_id))
        elif action == "existing":
            return redirect(url_for("existing_lists", user_id=user_id))

    return render_template("home.html")

@app.route("/existing/<user_id>", methods=["GET", "POST"])
def existing_lists(user_id):
    if request.method == "POST":
        list_id = request.form.get("list_id")  
        return redirect(url_for("shopping_list", user_id=user_id, list_id=list_id))

    lists = load_existing_lists(user_id)
    return render_template("existing_lists.html", user_id=user_id, lists=lists)

@app.route("/list/<user_id>/<list_id>", methods=["GET", "POST"])
def shopping_list(user_id, list_id):
    shopping_list = shopping_lists.get((user_id, list_id))
    if not shopping_list:
        shopping_list = ShoppingList()
        shopping_list.set_id(list_id)
        shopping_list.set_replica_id(int(user_id))
        file_path = os.path.join("userdata", str(user_id), f"{list_id}.txt")
        if os.path.exists(file_path):
            shopping_list.fillFromFile(file_path)
        shopping_lists[(user_id, list_id)] = shopping_list

    if request.method == "POST":
        data = request.json
        action = data.get("action")

        if action == "add":
            name = data["name"]
            quantity = data["quantity"]
            item_id = str(uuid.uuid4())
            shopping_list.add_item(item_id, {"name": name, "quantity": quantity, "acquired": False, "timestamp": shopping_list.increment_counter()})
        elif action == "remove":
            name = data["name"]
            shopping_list.remove_item(name)
        elif action == "increase":
            name = data["name"]
            item_id = shopping_list.get_item_id_by_name(name)
            if item_id:
                shopping_list.increment_quantity(item_id)
        elif action == "decrease":
            name = data["name"]
            item_id = shopping_list.get_item_id_by_name(name)
            if item_id:
                shopping_list.decrement_quantity(item_id)
        elif action == "acquire":
            name = data["name"]
            item_id = shopping_list.get_item_id_by_name(name)
            if item_id:
                shopping_list.update_acquired_status(item_id, True)
        elif action == "get":
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.connect("tcp://localhost:5051")
            socket.send_string(f"get{list_id}")
            response = socket.recv_string()
            print(response)
            if response != "":
                file_path = os.path.join("userdata", str(user_id), f"{list_id}.txt")
                with open(f"{file_path}",'w') as g:
                    g.write(response)
                shopping_list = ShoppingList()
                shopping_list.fillFromFile(file_path)
                shopping_list.set_replica_id(int(user_id))
                shopping_lists[(user_id, list_id)] = shopping_list
            socket.close()
        elif action == "synchronize":
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.connect("tcp://localhost:5051")
            shopping_list.localSave()
            file_path = os.path.join("userdata", str(user_id), f"{list_id}.txt")
            with open(f"{file_path}",'r') as f:
                message = f.read()
            socket.send_string(message)
            response = socket.recv_string()
            print(response)
            with open(f"{file_path}",'w') as g:
                g.write(response)
            shopping_list = ShoppingList()
            shopping_list.fillFromFile(file_path)
            shopping_list.set_replica_id(int(user_id))
            shopping_lists[(user_id, list_id)] = shopping_list
            """remote_list = ShoppingList()
            remote_list.set_id(shopping_list.my_id())
            remote_list.set_replica_id(int(user_id) + 1)
            shopping_list.merge(remote_list)"""
            socket.close()

        shopping_list.localSave()
        return jsonify({"status": "success"})

    return render_template(
        "shopping_list.html",
        user_id=user_id,
        list_id=list_id,
        items=shopping_list.shopping_map
    )

if __name__ == "__main__":
    app.run(debug=True)
