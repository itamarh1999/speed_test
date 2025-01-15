# test_connection.py
import socket
import time

def run_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    while True:
        message = b"Hello, Client!"
        sock.sendto(message, ('255.255.255.255', 13117))
        print(f"Sent broadcast message at {time.strftime('%H:%M:%S')}")
        time.sleep(1)

def run_client():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(('', 13117))
    
    print("Waiting for broadcast messages...")
    while True:
        data, addr = sock.recvfrom(1024)
        print(f"Received '{data.decode()}' from {addr}")

if __name__ == "__main__":
    role = input("Enter 'server' or 'client': ").strip().lower()
    if role == 'server':
        run_server()
    else:
        run_client()