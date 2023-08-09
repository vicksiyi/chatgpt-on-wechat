import socket
import threading

def receive_messages(client_socket):
    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            message = data.decode("utf-8")
            print("Received:", message)
    except Exception as e:
        print("Receive error:", e)
    finally:
        client_socket.close()

host = 'localhost'
port = 12344

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((host, port))

receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
receive_thread.start()

try:
    while True:
        message = input()
        if message.lower() == 'exit':
            break
        client_socket.send(message.encode("utf-8"))
except KeyboardInterrupt:
    pass
finally:
    client_socket.close()
