import zmq
import time
def client():
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5051")

    try:
        for i in range(5):
            message = f"list_id:{i}\ntest" 
            print(f"Client sending: {message}")
            socket.send_string(message)
            response = socket.recv_string()
            print(f"Client received: {response}")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nClient stopped by user.")

if __name__ == "__main__":
    client()

    

##########
"""
def synchronise(self):
    context = zmq.Context()
    socket = context.socket(zmq.REQ) 
    socket.connect("tcp://localhost:5051")

    with open(f"{self.list_id}.txt", 'r') as f:
        content = f.read()

    print(f"Synchronizing with server")
    socket.send_string(content)
    response = socket.recv_string()
    print(f"Synchronized")

    with open(f"{self.list_id}.txt", 'w') as f:
        f.write(response)

    Shoppinglist.fillfromfile(f"{self.list_id}.txt")

"""