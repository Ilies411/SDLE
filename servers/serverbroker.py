import zmq
import threading
import time

stop_event = threading.Event()
hints_queue = []

def run_broker():
    context = zmq.Context()
    router_socket = context.socket(zmq.ROUTER)
    router_socket.bind("tcp://*:4000")  

    print("Router started and waiting for messages from servers...")

    while not stop_event.is_set():
        try:
            message_parts = router_socket.recv_multipart(flags=zmq.NOBLOCK)
            if message_parts:
                sender = message_parts[0]
                target = message_parts[1]
                print(f"{message_parts}, Router received message from {sender} to {target}, {message_parts[-1].decode()}, content : {message_parts[-2].decode()}")
                if message_parts[-1].decode() == 'REPLICA':
                    router_socket.send_multipart([target, b'',message_parts[-2], b'REPLICA'])
                elif message_parts[-1].decode() == 'HINT':
                    router_socket.send_multipart([target, b'',sender,b'',message_parts[-2], b'HINT'])
                elif message_parts[-1].decode() == 'ACK':
                    router_socket.send_multipart([target, b'',sender,message_parts[-2], b'ACK'])
                elif message_parts[-1].decode() == 'MIGRATEDATA':
                    router_socket.send_multipart([target, b'',sender,message_parts[-2], b'MIGRATEDATA'])
        except zmq.Again:
            pass

if __name__ == "__main__":
    try:
        run_broker()
        while not stop_event.is_set():
            time.sleep(1)  
    except KeyboardInterrupt:
        print("\nShutting down broker...")
        stop_event.set()