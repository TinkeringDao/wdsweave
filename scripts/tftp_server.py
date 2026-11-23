#!/usr/bin/env python3
"""
Lightweight standalone RFC 1350 TFTP Server for OpenWrt Deco Recovery Bootstrap.
Zero dependencies. Pure Python standard library.
Listens on UDP port 69 (or custom port).
Serves files from a designated directory (default: firmware/tftp_stage).
"""

import argparse
import os
import socket
import struct
import sys
import time

OP_RRQ = 1
OP_WRQ = 2
OP_DATA = 3
OP_ACK = 4
OP_ERROR = 5

BLOCK_SIZE = 512
TIMEOUT_SEC = 3.0
MAX_RETRIES = 5

class TftpServer:
    def __init__(self, host: str, port: int, root_dir: str):
        self.host = host
        self.port = port
        self.root_dir = os.path.abspath(root_dir)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = False
        self.last_transferred_file = None

    def start(self):
        try:
            self.sock.bind((self.host, self.port))
            self.sock.settimeout(1.0)
            self.running = True
        except PermissionError:
            print(f"[!] Permission denied binding to {self.host}:{self.port}. Run with sudo if using port 69.")
            sys.exit(1)

        print(f"[*] TFTP server listening on {self.host}:{self.port}")
        print(f"[*] Serving files from: {self.root_dir}")
        print("[*] Waiting for client requests...")

        while self.running:
            try:
                data, client_addr = self.sock.recvfrom(2048)
                if len(data) < 4:
                    continue
                opcode = struct.unpack(">H", data[:2])[0]
                if opcode == OP_RRQ:
                    self.handle_rrq(data[2:], client_addr)
                elif opcode == OP_WRQ:
                    self.send_error(self.sock, client_addr, 4, "Write requests not permitted")
            except socket.timeout:
                continue
            except KeyboardInterrupt:
                print("\n[*] TFTP server stopped by user.")
                break
            except Exception as e:
                if self.running:
                    print(f"[!] Server loop error: {e}")

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass

    def handle_rrq(self, payload: bytes, client_addr: tuple):
        # Extract filename and mode
        null_idx = payload.find(b"\x00")
        if null_idx == -1:
            return
        filename = payload[:null_idx].decode(errors="replace")
        mode = payload[null_idx+1:].split(b"\x00")[0].decode(errors="replace").lower()

        # Sanitize filename
        clean_filename = os.path.basename(filename)
        file_path = os.path.join(self.root_dir, clean_filename)

        print(f"\n[+] RRQ from {client_addr[0]}:{client_addr[1]} for '{clean_filename}' (mode: {mode})")

        if not os.path.isfile(file_path):
            print(f"[-] File not found: {file_path}")
            self.send_error(self.sock, client_addr, 1, f"File not found: {clean_filename}")
            return

        file_size = os.path.getsize(file_path)
        print(f"[+] Found file: {clean_filename} ({file_size:,} bytes). Initiating transfer...")

        # Spawn a dedicated client socket for this transfer session (TID)
        session_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        session_sock.settimeout(TIMEOUT_SEC)

        try:
            with open(file_path, "rb") as f:
                block_num = 1
                bytes_sent = 0
                start_time = time.time()

                while True:
                    chunk = f.read(BLOCK_SIZE)
                    data_pkt = struct.pack(">HH", OP_DATA, block_num) + chunk

                    retries = 0
                    ack_received = False

                    while retries < MAX_RETRIES:
                        session_sock.sendto(data_pkt, client_addr)

                        try:
                            resp, ack_addr = session_sock.recvfrom(516)
                            if len(resp) >= 4:
                                resp_op, ack_num = struct.unpack(">HH", resp[:4])
                                if resp_op == OP_ACK and ack_num == block_num:
                                    ack_received = True
                                    client_addr = ack_addr  # update TID
                                    break
                                elif resp_op == OP_ERROR:
                                    print(f"[-] Client reported error: {resp[4:].decode(errors='replace')}")
                                    return
                        except socket.timeout:
                            retries += 1
                            print(f"[!] Timeout waiting for ACK {block_num}, retry {retries}/{MAX_RETRIES}...")

                    if not ack_received:
                        print(f"[-] Transfer failed: ACK {block_num} never received after {MAX_RETRIES} retries.")
                        return

                    bytes_sent += len(chunk)
                    if block_num % 100 == 0 or len(chunk) < BLOCK_SIZE:
                        pct = (bytes_sent / file_size) * 100 if file_size else 100
                        sys.stdout.write(f"\r[+] Sent {bytes_sent:,} / {file_size:,} bytes ({pct:.1f}%) [Block {block_num}]")
                        sys.stdout.flush()

                    if len(chunk) < BLOCK_SIZE:
                        elapsed = max(time.time() - start_time, 0.001)
                        speed_kb = (bytes_sent / 1024) / elapsed
                        print(f"\n[+] Transfer of '{clean_filename}' complete: {bytes_sent:,} bytes in {elapsed:.2f}s ({speed_kb:.1f} KB/s)")
                        self.last_transferred_file = clean_filename
                        break

                    block_num = (block_num + 1) & 0xFFFF
        finally:
            session_sock.close()

    def send_error(self, sock: socket.socket, addr: tuple, code: int, msg: str):
        err_pkt = struct.pack(">HH", OP_ERROR, code) + msg.encode() + b"\x00"
        sock.sendto(err_pkt, addr)


def main():
    parser = argparse.ArgumentParser(description="Standalone TFTP Server for Router Recovery")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface IP (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=69, help="UDP port (default: 69)")
    parser.add_argument("--root", default="firmware/tftp_stage", help="Root directory to serve files from")
    args = parser.parse_args()

    server = TftpServer(args.host, args.port, args.root)
    server.start()

if __name__ == "__main__":
    main()
