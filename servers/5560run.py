from servers.newboostedserv import * 

if __name__ == "__main__":
    try:
        ports = [5560]
        threads = []

        for port in ports:
            thread = threading.Thread(target=run_server, args=(port,))
            thread.daemon = True
            thread.start()
            threads.append(thread)

        print("Servers running. Press Ctrl+C to stop.")
        while not stop_event.is_set():
            time.sleep(0.1) 
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        stop_event.set()
    finally:
        print("All servers stopped.")