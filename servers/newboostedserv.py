import zmq
import threading
from CRDTShoppingList import *
import time
import os

stop_event = threading.Event()


def run_server(port):
    hints_queue = []

    context = zmq.Context()

    # Sockets
    lb_socket = context.socket(zmq.DEALER)
    lb_socket.identity = u"{}".format(port).encode()
    lb_socket.connect("tcp://localhost:6000")
    
    inter_server_socket = context.socket(zmq.DEALER)
    inter_server_socket.identity = u"{}".format(port+1000).encode()
    inter_server_socket.connect("tcp://localhost:4000")

    
    hint_socket = context.socket(zmq.DEALER)
    hint_socket.identity = u"{}".format(port+2000).encode()
    hint_socket.connect("tcp://localhost:4000")

    print(f"Server {port} started and connected to load balancer.")
    print(f"InterServer Socket {port+1000} binded.")
    print(f"Hint Socket {port+2000} binded.")

    folder_path = os.path.join("server_data", str(port))
    file_path = os.path.join(folder_path, "active_list.txt")
    os.makedirs(folder_path, exist_ok=True)

    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            print(f"{port} : Created active_list.txt")
    else:
        print(f"{port}: Server Data already exists")
    

    def replicate_to_servers(response,replica_ports):
        for replica_port in replica_ports:
            inter_server_socket.send_multipart(
                [str(replica_port+1000).encode(), b'', response.encode(), b'REPLICA']
            )
            print(f"replica_sent to {replica_port}")

    def handle_message(message_parts, load_socket, server_socket ):
        if message_parts[-1] == b'MIGRATEDATA':
            key = message_parts[-5].decode()
            print(f"{port} need to migrate data {key}")
            target = message_parts[-7].decode()
            target = int(target) + 1000
            target = str(target).encode()
            replicas = message_parts[-3]
            file_path = f"server_data/{port}/{key}.txt"
            with open(file_path,'r') as f:
                content = f.read()
            server_socket.send_multipart([target, b'', content.encode(),b'',replicas,b'', b'MIGRATEDATA'])
            if os.path.exists(file_path):
                os.remove(file_path)
        elif message_parts[-1] == b'DELETE':
            key = message_parts[-3].decode()
            file_path = f"server_data/{port}/{key}.txt"
            if os.path.exists(file_path):
                os.remove(file_path)
            print(f"{port} deleted key {key}")

    
        elif message_parts[-1] == b'HINT':
            hint_data = (message_parts[-5].decode() if isinstance(message_parts[-5], bytes) else message_parts[-5],
             message_parts[-3].decode() if isinstance(message_parts[-3], bytes) else message_parts[-3])
            hints_queue.append(hint_data)
            print(f"Hint added to queue: {hint_data}")
            print(f"queue : {hints_queue}")
            response = message_parts[-5]
            print("sending response")
            load_socket.send_multipart([message_parts[1], b'', response])
        else:
            clientlistid = message_parts[-1].decode().split("_",2)[1]
            with open(f'server_data/{port}/active_list.txt', 'r+') as f:
                    data = f.readlines()
                    if f"{clientlistid}\n" not in data:
                        f.write(f"{clientlistid}\n")

            server_file = f'server_data/{port}/{clientlistid}.txt'
            if not os.path.exists(server_file):
                with open(server_file, 'w') as g:
                    g.write(f"{message_parts[-1].decode()}")
                serverList = ShoppingList()
                serverList.fillFromFile(server_file)
                serverList.set_replica_id(int(port))
                serverList.increment_counter()
                serverList.localSave("server_data")
            else:
                temp_client = f'server_data/{port}/temp/{clientlistid}.txt'
                os.makedirs(os.path.dirname(temp_client), exist_ok=True)
                with open(temp_client, 'w') as g:
                    g.write(f"{message_parts[-1].decode()}")
                clientList = ShoppingList()
                clientList.fillFromFile(temp_client)
                serverList = ShoppingList()
                serverList.fillFromFile(server_file)
                serverList.set_replica_id(int(port))
                serverList.merge(clientList)
                serverList.increment_counter()
                serverList.localSave("server_data")
            
            with open(server_file, 'r') as h:
                response = h.read()
            
            load_socket.send_multipart([message_parts[1], b'', response.encode()])

            replica_ports = message_parts[-3].decode().split(",")
            print(f"replica_ports: {replica_ports}")
            replica_ports = [int(x) for x in replica_ports]
            replicate_to_servers(response,replica_ports)

    def handle_server_message(message_parts, socket):
        print("hello")
        if message_parts[-1] == b'REPLICA':
            clientlistid = message_parts[-2].decode().split("_",2)[1]
            server_file = f'server_data/{port}/{clientlistid}.txt'
            with open(server_file, 'w') as g:
                    g.write(f"{message_parts[-2].decode()}")
            print(f"Server {port} received replica")
        elif message_parts[-1] == b'MIGRATEDATA':
            print("received migration of data")
            content = message_parts[-5].decode()
            clientlistid = content.split("_",2)[1]
            server_file = f'server_data/{port}/{clientlistid}.txt'
            with open(server_file, 'w') as g:
                    g.write(f"{message_parts[-2].decode()}")
            with open(f'server_data/{port}/active_list.txt', 'r+') as f:
                    data = f.readlines()
                    if f"{clientlistid}\n" not in data:
                        f.write(f"{clientlistid}\n")
            replica_ports = message_parts[-3].decode().split(",")
            print(f"replica_ports: {replica_ports}")
            replica_ports = [int(x) for x in replica_ports]
            replicate_to_servers(content,replica_ports)
        elif message_parts[-1] == b'HINT':
            print(message_parts)
            sender = message_parts[-4]
            content = message_parts[-2]

            clientlistid = content.decode().split("_",2)[1]
            with open(f'server_data/{port}/active_list.txt', 'r+') as f:
                    data = f.readlines()
                    if f"{clientlistid}\n" not in data:
                        f.write(f"{clientlistid}\n")

            server_file = f'server_data/{port}/{clientlistid}.txt'
            if not os.path.exists(server_file):
                with open(server_file, 'w') as g:
                    g.write(f"{content.decode()}")
                serverList = ShoppingList()
                serverList.fillFromFile(server_file)
                serverList.set_replica_id(int(port))
                serverList.increment_counter()
                serverList.localSave("server_data")
            else:
                temp_client = f'server_data/{port}/temp/{clientlistid}.txt'
                os.makedirs(os.path.dirname(temp_client), exist_ok=True)
                with open(temp_client, 'w') as g:
                    g.write(f"{content.decode()}")
                clientList = ShoppingList()
                clientList.fillFromFile(temp_client)
                serverList = ShoppingList()
                serverList.fillFromFile(server_file)
                serverList.set_replica_id(int(port))
                serverList.increment_counter() #after merge i think
                serverList.merge(clientList)
                serverList.localSave("server_data")

            print(f"{port} received its hint now send ack" )
            print(f"sender was {sender.decode()}")
            int_sender = int(sender.decode()) - 1000
            socket.send_multipart([str(int_sender).encode(), b'', content, b'ACK'])

        elif message_parts[-1] == b'ACK':
            print("WWWWWWWWWWWWW")
            sender = message_parts[-3].decode()
            message = message_parts[-2].decode()
            int_sender = int(sender) - 1000
            hints_queue.remove((message,str(int_sender)))
            print(f"{sender} removed from hints queue")

    def process_hints():
        while not stop_event.is_set():
            if hints_queue:
                for message, target in list(hints_queue):
                    target_int = int(target) + 1000
                    hint_socket.send_multipart([(str(target_int)).encode(), b'', message.encode(), b'HINT'])
                    print(f"Hint sent to target {target_int}")
                    time.sleep(5)  
            else:
                time.sleep(5)
                    

    def loadbalancercomm():
        last_heartbeat = time.time()
        while not stop_event.is_set():
            try:
                message_parts = lb_socket.recv_multipart(flags=zmq.NOBLOCK)
                print(f"{port}received a client messag")
                if message_parts:
                    handle_message(message_parts, lb_socket, inter_server_socket)
            except zmq.Again:
                pass

            # heartbeat
            if time.time() - last_heartbeat > 2:
                lb_socket.send_multipart([b'', b'', b'HEARTBEAT'])
                last_heartbeat = time.time()

    def listen_servers():
        while not stop_event.is_set():
            try:
                message_parts = inter_server_socket.recv_multipart(flags=zmq.NOBLOCK)
                print(f"{port} received a mes from a serv")
                handle_server_message(message_parts, inter_server_socket)
            except zmq.Again:
                pass

    threading.Thread(target=loadbalancercomm, daemon=True).start()
    threading.Thread(target=listen_servers, daemon=True).start()
    threading.Thread(target=process_hints, daemon=True).start()

from multiprocessing import Process

if __name__ == "__main__":
    try:
        ports = [5556,5557,5558,5559]
        threads = []

        for port in ports:
            thread = threading.Thread(target=run_server, args=(port,))
            thread.daemon = True
            thread.start()
            threads.append(thread)

        print("Servers running. Press Ctrl+C to stop.")
        while not stop_event.is_set():
            time.sleep(1)  
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        stop_event.set()
    finally:
        print("All servers stopped.")

