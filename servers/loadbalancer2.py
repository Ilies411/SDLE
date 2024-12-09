import hashlib  
import zmq
import time
from bisect import bisect_left
import os

class ConsistentHashing:
    def __init__(self, vnodes=3):
        self.vnodes = vnodes
        self.ring = {}
        self.sorted_keys = []

    def _hash(self, key):
        return int(hashlib.sha256(key.encode('utf-8')).hexdigest(), 16)

    def add_node(self, node):
        for i in range(self.vnodes):
            hashed_key = self._hash(f"{node}-{i}")
            self.ring[hashed_key] = node
            self.sorted_keys.append(hashed_key)
        self.sorted_keys.sort()

    def get_node(self, key):
        hashed_key = self._hash(key)
        idx = bisect_left(self.sorted_keys, hashed_key)
        if idx == len(self.sorted_keys):
            idx = 0
        return self.ring[self.sorted_keys[idx]]

    def get_preference_list(self, key, num_replicas=2):
        hashed_key = self._hash(key)
        idx = bisect_left(self.sorted_keys, hashed_key)

        preference_list = []

        for i in range(len(self.sorted_keys)):
            current_idx = (idx + i) % len(self.sorted_keys)
            physical_node = self.ring[self.sorted_keys[current_idx]]
        
            if physical_node not in preference_list:
                preference_list.append(physical_node)

            if len(preference_list) == num_replicas:
                break

        return preference_list
    
    def get_hint(self,list_id):
        preference_list = self.get_preference_list(str(list_id))
        if not preference_list:
            raise ValueError("Preference list is empty.")
        last = preference_list[-1]
        found_hint = False
        while not found_hint:
            target_hint = self.get_node(str(last))
            if target_hint not in preference_list:
                found_hint = True
            else:
                last = target_hint
        return target_hint

"""
A = ConsistentHashing(3)

A.add_node(5556)
A.add_node(5557)
A.add_node(5560)
A.add_node(5558)
A.add_node(5559)

print(A.get_node("0"))
print(A.get_node("1"))
print(A.get_node("2"))
print(A.get_node("3"))
print(A.get_node("4"))
print(A.get_preference_list("hello",3))
print(A.get_preference_list("a",5))

"""
def load_balancer():
    context = zmq.Context()

    # Sockets
    frontend = context.socket(zmq.ROUTER)
    frontend.bind("tcp://*:5051")
    backend = context.socket(zmq.ROUTER)
    backend.bind("tcp://*:6000")

    poller = zmq.Poller()
    poller.register(frontend, zmq.POLLIN)
    poller.register(backend, zmq.POLLIN)

    # Initialisation
    server_ports = [5556, 5557, 5558, 5559, 5560]
    ring = ConsistentHashing(3)
    for port in server_ports:
        ring.add_node(port)

    HEARTBEAT_INTERVAL = 3  
    ACTIVE_CHECK_INTERVAL = 1000  
    last_heartbeat = {port: time.time() for port in server_ports}
    active_servers = set(server_ports)

    print("Load balancer is running...")

    while True:
        try:
            events = dict(poller.poll(ACTIVE_CHECK_INTERVAL))
            
            if frontend in events:
                client_id, empty, client_message = frontend.recv_multipart()
                print(f"Reçu de client : {client_message.decode()}")

                list_id = client_message.decode().split("\n")[0].split(":")[1]
                preference_list = ring.get_preference_list(list_id)
                target_server = preference_list[0]

                if target_server in active_servers:
                    print(f"Transfert vers serveur actif {target_server}")
                    backend.send_multipart([str(target_server).encode(), b'', client_id, b'', client_message])
                else:
                    hint = ring.get_hint(list_id)
                    print(f"Serveur {target_server} inactif, transfert vers {hint}")
                    backend.send_multipart([str(hint).encode(), b'', client_id, b'', client_message,b'',str(target_server).encode(),b'',b'HINT'])

            if backend in events:
                server_address, client_id, empty2, server_response = backend.recv_multipart()
                if server_response.decode() == 'HEARTBEAT':
                    port = int(server_address.decode())
                    last_heartbeat[port] = time.time()
                    print(f"Heartbeat reçu de {port}")
                else:
                    print(f"Réponse pour client {client_id}: {server_response.decode()}")
                    frontend.send_multipart([client_id, b'', server_response])

            current_time = time.time()
            for port, last_time in last_heartbeat.items():
                if current_time - last_time > HEARTBEAT_INTERVAL:
                    if port in active_servers:
                        active_servers.remove(port)
                else:
                    if port not in active_servers:
                        active_servers.add(port)
            if os.name == 'nt':  
                os.system('cls')
            else:  
                print("\033c", end="")  
            for port in server_ports:
                status = "Alive" if port in active_servers else "Dead"
                print(f"Server {port} : {status}") 
            

        except KeyboardInterrupt:
            print("\nArrêt du load balancer.")
            break
        except Exception as e:
            print(f"Erreur : {e}")
            break


if __name__ == "__main__":
    load_balancer()


"""
que reste il a faire : 
    - definir un register push/pull ou autre pour avoir le cpu load
    - mecanisme de réplique
    - créer les server datas
    - clé privé/public pour plus de sécurité
    - frontentd
"""








