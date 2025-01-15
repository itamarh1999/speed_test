# client.py
import socket
import threading
import struct
import time
import logging

class SpeedTestClient:
    def __init__(self):
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Client configuration
        self.magic_cookie = 0xabcddcba
        self.running = True
        self.buffer_size = 4096

    def start(self):
        while self.running:
            try:
                # Get user input
                file_size = int(input("Enter file size (bytes): "))
                tcp_connections = int(input("Enter number of TCP connections: "))
                udp_connections = int(input("Enter number of UDP connections: "))

                if file_size <= 0 or tcp_connections < 0 or udp_connections < 0:
                    raise ValueError("Invalid input values")

                self.logger.info("Client started, listening for offer requests...")
                
                # Listen for server offers
                server_info = self.listen_for_offer()
                if server_info:
                    server_ip, udp_port, tcp_port = server_info
                    self.logger.info(f"Received offer from {server_ip}")

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

                    self.logger.info("All transfers complete")

            except ValueError as e:
                self.logger.error(f"Invalid input: {e}")
            except Exception as e:
                self.logger.error(f"Error in client: {e}")

    def listen_for_offer(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            # Try to bind to specific address first
            try:
                sock.bind(('', 13117))
            except:
                sock.bind(('0.0.0.0', 13117))
                
            self.logger.info("Listening for broadcasts...")
            sock.settimeout(1)  # Add timeout to show we're still alive
            
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    self.logger.info(f"Received data from {addr}")
                    
                    magic_cookie, msg_type, udp_port, tcp_port = struct.unpack('!IbHH', data)
                    
                    if magic_cookie == self.magic_cookie and msg_type == 0x2:
                        self.logger.info(f"Valid offer received from {addr[0]}:{addr[1]}")
                        return (addr[0], udp_port, tcp_port)
                        
                except socket.timeout:
                    self.logger.info("Still waiting for server broadcast...")
                except struct.error:
                    self.logger.warning("Received malformed packet")
                    
        except Exception as e:
            self.logger.error(f"Error in offer listener: {e}")
        finally:
            sock.close()

    def tcp_test(self, server_ip, port, file_size, connection_num):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            start_time = time.time()
            sock.connect((server_ip, port))
            
            # Send file size request
            sock.send(f"{file_size}\n".encode())
            
            # Receive data
            received = 0
            while received < file_size:
                data = sock.recv(self.buffer_size)
                if not data:
                    break
                received += len(data)

            duration = time.time() - start_time
            speed = (file_size * 8) / duration  # bits per second

            self.logger.info(
                f"TCP transfer #{connection_num} finished:\n"
                f"Time: {duration:.3f} seconds\n"
                f"Speed: {speed:.1f} bits/second"
            )

        except Exception as e:
            self.logger.error(f"Error in TCP test #{connection_num}: {e}")
        finally:
            sock.close()

    def udp_test(self, server_ip, port, file_size, connection_num):
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
                    data, _ = sock.recvfrom(self.buffer_size)
                    last_receive_time = time.time()

                    header_size = struct.calcsize('!IbQQ')
                    magic_cookie, msg_type, total_segs, current_seg = struct.unpack(
                        '!IbQQ', data[:header_size])

                    if magic_cookie == self.magic_cookie and msg_type == 0x4:
                        total_segments = total_segs
                        received_segments.add(current_seg)

                except socket.timeout:
                    if time.time() - last_receive_time >= 1.0:
                        break

            duration = time.time() - start_time
            if total_segments:
                success_rate = (len(received_segments) / total_segments) * 100
                speed = (file_size * 8) / duration

                self.logger.info(
                    f"UDP transfer #{connection_num} finished:\n"
                    f"Time: {duration:.3f} seconds\n"
                    f"Speed: {speed:.1f} bits/second\n"
                    f"Success rate: {success_rate:.1f}%"
                )

        except Exception as e:
            self.logger.error(f"Error in UDP test #{connection_num}: {e}")
        finally:
            sock.close()

if __name__ == "__main__":
    client = SpeedTestClient()
    client.start()