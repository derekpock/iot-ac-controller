import socket

HOST = "10.0.0.140"
PORT = 53892

with socket.create_connection((HOST, PORT)) as sock:
    sock.sendall(b"temp:1020.30")
