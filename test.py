import socket
import threading

def handle_client(client_socket):
    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            message = data.decode()
            print("Received:", message)
            broadcast(message, client_socket)
    except Exception as e:
        print("Client error:", e)
    finally:
        client_sockets.remove(client_socket)
        client_socket.close()

def broadcast(message, sender_socket):
    for client_socket in client_sockets:
        if client_socket != sender_socket:
            try:
                client_socket.send(message.encode())
            except:
                client_socket.close()
                client_sockets.remove(client_socket)

host = '0.0.0.0'
port = 12345

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((host, port))
server_socket.listen(5)

print("Server listening on", host, "port", port)

client_sockets = []

try:
    while True:
        client_socket, client_address = server_socket.accept()
        client_sockets.append(client_socket)
        print("Accepted connection from", client_address)
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        client_handler.start()
except KeyboardInterrupt:
    pass
finally:
    for client_socket in client_sockets:
        client_socket.close()
    server_socket.close()
