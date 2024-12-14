import zmq
import threading
import time

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
            server_socket.send_multipart([target, b'', key.encode(),b'',replicas,b'', b'MIGRATEDATA'])
        
        elif message_parts[-1] == b'DELETE':
            key = message_parts[-3].decode()
            print(f"{port} deleted key {key}")

    
        elif message_parts[-1] == b'HINT':
            hint_data = (message_parts[-5].decode() if isinstance(message_parts[-5], bytes) else message_parts[-5],
             message_parts[-3].decode() if isinstance(message_parts[-3], bytes) else message_parts[-3])
            hints_queue.append(hint_data)
            print(f"Hint added to queue: {hint_data}")
            print(f"queue : {hints_queue}")
            response = f"Response from server {port}, responsible of the hint"
            print("sending response")
            load_socket.send_multipart([message_parts[1], b'', response.encode()])
        else:
            #replicate_to_servers(response) may delete
            response = f"Response from server {port}"
            print("sending response")
            load_socket.send_multipart([message_parts[1], b'', response.encode()])
            replica_ports = message_parts[-3].decode().split(",")
            print(f"replica_ports: {replica_ports}")
            replica_ports = [int(x) for x in replica_ports]
            replicate_to_servers(response,replica_ports)

    def handle_server_message(message_parts, socket):
        print("hello")
        if message_parts[-1] == b'REPLICA':
            print(f"Server {port} received replica")
        elif message_parts[-1] == b'MIGRATEDATA':
            print("received migration opf data")
            key = message_parts[-5].decode()
            replica_ports = message_parts[-3].decode().split(",")
            print(f"replica_ports: {replica_ports}")
            replica_ports = [int(x) for x in replica_ports]
            replicate_to_servers(key,replica_ports)
        elif message_parts[-1] == b'HINT':
            print(message_parts)
            sender = message_parts[-4]
            message = message_parts[-2]
            print(f"{port} received its hint now send ack" )
            print(f"sender was {sender.decode()}")
            int_sender = int(sender.decode()) - 1000
            socket.send_multipart([str(int_sender).encode(), b'', message, b'ACK'])
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

