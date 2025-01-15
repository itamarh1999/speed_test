# client.py
import socket
import threading
import struct
import time

class SpeedTestClient:
    def __init__(self):
        self.magic_cookie = 0xabcddcba
        self.running = True

    def start(self):
        while self.running:
            # Get user input
            file_size = int(input("Enter file size (bytes): "))
            tcp_connections = int(input("Enter number of TCP connections: "))
            udp_connections = int(input("Enter number of UDP connections: "))

            print("Client started, listening for offer requests...")
            
            # Listen for server offers
            server_info = self.listen_for_offer()
            if server_info:
                server_ip, udp_port, tcp_port = server_info
                print(f"Received offer from {server_ip}")

                # Start speed tests
                threads = []
                
                # Start TCP tests
                for i in range(tcp_connections):
                    thread = threading.Thread(target=self.tcp_test, 
                                           args=(server_ip, tcp_port, file_size, i+1))
                    threads.append(thread)
                    thread.start()

                # Start UDP tests
                for i in range(udp_connections):
                    thread = threading.Thread(target=self.udp_test, 
                                           args=(server_ip, udp_port, file_size, i+1))
                    threads.append(thread)
                    thread.start()

                # Wait for all tests to complete
                for thread in threads:
                    thread.join()

                print("All transfers complete, listening to offer requests")

    def listen_for_offer(self):
        # Create UDP socket for listening to offers
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        sock.bind(('', 13117))

        while True:
            try:
                data, addr = sock.recvfrom(1024)
                magic_cookie, msg_type, udp_port, tcp_port = struct.unpack('!IbHH', data)
                
                if magic_cookie == self.magic_cookie and msg_type == 0x2:
                    sock.close()
                    return (addr[0], udp_port, tcp_port)
            except:
                continue

    def tcp_test(self, server_ip, port, file_size, connection_num):
        # Create TCP connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            start_time = time.time()
            sock.connect((server_ip, port))
            
            # Send file size request
            sock.send(f"{file_size}\n".encode())
            
            # Receive data
            received = 0
            while received < file_size:
                data = sock.recv(4096)
                if not data:
                    break
                received += len(data)

            duration = time.time() - start_time
            speed = (file_size * 8) / duration  # bits per second

            print(f"\033[92mTCP transfer #{connection_num} finished, "
                  f"total time: {duration:.3f} seconds, "
                  f"total speed: {speed:.1f} bits/second\033[0m")

        finally:
            sock.close()

    def udp_test(self, server_ip, port, file_size, connection_num):
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Send request
            request = struct.pack('!IbQ', self.magic_cookie, 0x3, file_size)
            sock.sendto(request, (server_ip, port))

            start_time = time.time()
            received_segments = set()
            total_segments = None
            last_receive_time = time.time()

            while True:
                try:
                    sock.settimeout(1.0)
                    data, _ = sock.recvfrom(4096)
                    last_receive_time = time.time()

                    # Unpack header
                    header_size = struct.calcsize('!IbQQ')
                    magic_cookie, msg_type, total_segs, current_seg = struct.unpack('!IbQQ', data[:header_size])

                    if magic_cookie == self.magic_cookie and msg_type == 0x4:
                        total_segments = total_segs
                        received_segments.add(current_seg)

                except socket.timeout:
                    if time.time() - last_receive_time >= 1.0:
                        break

            duration = time.time() - start_time
            if total_segments:
                success_rate = (len(received_segments) / total_segments) * 100
                speed = (file_size * 8) / duration  # bits per second

                print(f"\033[94mUDP transfer #{connection_num} finished, "
                      f"total time: {duration:.3f} seconds, "
                      f"total speed: {speed:.1f} bits/second, "
                      f"percentage of packets received successfully: {success_rate:.1f}%\033[0m")

        finally:
            sock.close()

if __name__ == "__main__":
    client = SpeedTestClient()
    client.start()