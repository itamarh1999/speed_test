# server.py
import socket
import threading
import struct
import time
import random

class SpeedTestServer:
    def __init__(self):
        # Initialize server parameters
        self.udp_port = random.randint(10000, 65000)
        self.tcp_port = random.randint(10000, 65000)
        self.magic_cookie = 0xabcddcba
        self.running = True

    def start(self):
        # Start UDP broadcast thread
        broadcast_thread = threading.Thread(target=self.send_offers)
        broadcast_thread.daemon = True
        broadcast_thread.start()

        # Start TCP listener
        tcp_thread = threading.Thread(target=self.tcp_listener)
        tcp_thread.daemon = True
        tcp_thread.start()

        # Start UDP listener
        udp_thread = threading.Thread(target=self.udp_listener)
        udp_thread.daemon = True
        udp_thread.start()

        print(f"Server started, listening on IP address {socket.gethostbyname(socket.gethostname())}")
        
        while True:
            time.sleep(1)

    def send_offers(self):
        # Create UDP broadcast socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        while self.running:
            # Create offer message
            message = struct.pack('!IbHH', 
                                self.magic_cookie,    # Magic cookie
                                0x2,                  # Message type (offer)
                                self.udp_port,        # UDP port
                                self.tcp_port)        # TCP port
            
            # Broadcast offer
            sock.sendto(message, ('<broadcast>', 13117))
            time.sleep(1)

    def tcp_listener(self):
        # Set up TCP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', self.tcp_port))
        sock.listen(5)

        while self.running:
            client, addr = sock.accept()
            # Handle TCP connection in new thread
            thread = threading.Thread(target=self.handle_tcp_client, args=(client,))
            thread.daemon = True
            thread.start()

    def handle_tcp_client(self, client):
        try:
            # Get file size from client
            file_size = int(client.recv(1024).decode().strip())
            # Send random data of requested size
            data = B'x' * file_size
            client.sendall(data)
        finally:
            client.close()

    def udp_listener(self):
        # Set up UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', self.udp_port))

        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                # Handle UDP request in new thread
                thread = threading.Thread(target=self.handle_udp_client, args=(sock, data, addr))
                thread.daemon = True
                thread.start()
            except:
                continue

    def handle_udp_client(self, sock, data, addr):
        # Unpack request message
        magic_cookie, msg_type, file_size = struct.unpack('!IbQ', data)
        
        if magic_cookie != self.magic_cookie or msg_type != 0x3:
            return

        # Calculate number of segments
        segment_size = 1400
        total_segments = (file_size + segment_size - 1) // segment_size

        # Send data in segments
        for i in range(total_segments):
            payload = b'x' * min(segment_size, file_size - i * segment_size)
            message = struct.pack('!IbQQ', 
                                self.magic_cookie,    # Magic cookie
                                0x4,                  # Message type (payload)
                                total_segments,       # Total segments
                                i)                    # Current segment
            message += payload
            sock.sendto(message, addr)
            time.sleep(0.00001)  # Small delay to prevent overwhelming the network

if __name__ == "__main__":
    server = SpeedTestServer()
    server.start()