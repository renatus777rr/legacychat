#!/usr/bin/env python3
import socket
import threading
import json

class LegacyChatServer:
    def __init__(self, host, port):
        self.server_address = (host, port)
        # Data store: username -> {'password': str, 'buddies': dict, 'messages': list}
        self.users = {}
        self.lock = threading.Lock()
        self.running = True

    def start(self):
        print("Starting LegacyChat Server on {}:{}".format(*self.server_address))
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(self.server_address)
        self.server_socket.listen(5)
        try:
            while self.running:
                client_socket, client_address = self.server_socket.accept()
                print("Connection from", client_address)
                threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
        except KeyboardInterrupt:
            print("Server is shutting down.")
        finally:
            self.server_socket.close()

    def handle_client(self, client_socket):
        """Simple line-delimited JSON protocol."""
        try:
            data_buffer = ""
            while True:
                data = client_socket.recv(4096).decode("utf-8")
                if not data:
                    break
                data_buffer += data
                if "\n" in data_buffer:
                    lines = data_buffer.split("\n")
                    for line in lines[:-1]:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            request = json.loads(line)
                            response = self.process_request(request)
                        except Exception as e:
                            response = {"status": "error", "message": str(e)}
                        client_socket.sendall((json.dumps(response) + "\n").encode("utf-8"))
                    data_buffer = lines[-1]
        except Exception as ex:
            print("Error handling client:", ex)
        finally:
            client_socket.close()

    def process_request(self, request):
        action = request.get("action")
        if action == "signup":
            return self.signup(request)
        elif action == "login":
            return self.login(request)
        elif action == "add_buddy":
            return self.add_buddy(request)
        elif action == "send_message":
            return self.send_message(request)
        elif action == "get_messages":
            return self.get_messages(request)
        elif action == "send_file":
            return self.send_file(request)
        else:
            return {"status": "error", "message": "Unknown action"}

    def signup(self, request):
        username = request.get("username")
        password = request.get("password")
        if not username or not password:
            return {"status": "error", "message": "Username and password required"}
        with self.lock:
            if username in self.users:
                return {"status": "error", "message": "Username already exists"}
            self.users[username] = {"password": password, "buddies": {}, "messages": []}
            print(f"New signup: {username}")
        return {"status": "success", "message": "User signed up"}

    def login(self, request):
        username = request.get("username")
        password = request.get("password")
        if not username or not password:
            return {"status": "error", "message": "Username and password required"}
        with self.lock:
            user = self.users.get(username)
            if user is None:
                return {"status": "error", "message": "User does not exist"}
            if user["password"] != password:
                return {"status": "error", "message": "Incorrect password"}
        # Return buddy list (simply the buddy names here)
        buddy_list = list(user["buddies"].values())
        return {"status": "success", "message": "User logged in", "buddies": buddy_list}

    def add_buddy(self, request):
        username = request.get("username")
        buddy_username = request.get("buddy_username")
        buddy_name = request.get("buddy_name")
        if not username or not buddy_username or not buddy_name:
            return {"status": "error", "message": "Missing fields for adding buddy"}
        with self.lock:
            if username not in self.users:
                return {"status": "error", "message": "User not found"}
            if buddy_username not in self.users:
                return {"status": "error", "message": "Buddy username does not exist"}
            self.users[username]["buddies"][buddy_username] = buddy_name
        return {"status": "success", "message": "Buddy added"}

    def send_message(self, request):
        sender = request.get("sender")
        recipient = request.get("recipient")
        message_text = request.get("message")
        if not sender or not recipient or not message_text:
            return {"status": "error", "message": "Missing fields for sending message"}
        with self.lock:
            if recipient not in self.users:
                return {"status": "error", "message": "Recipient does not exist"}
            msg = {"from": sender, "message": message_text}
            self.users[recipient]["messages"].append(msg)
        return {"status": "success", "message": "Message sent"}

    def send_file(self, request):
        sender = request.get("sender")
        recipient = request.get("recipient")
        filename = request.get("filename")
        filedata = request.get("filedata")
        if not sender or not recipient or not filename or not filedata:
            return {"status": "error", "message": "Missing fields for sending file"}
        with self.lock:
            if recipient not in self.users:
                return {"status": "error", "message": "Recipient does not exist"}
            # Mark the message as a file transfer with an extra "type" field.
            file_msg = {"from": sender, "filename": filename, "filedata": filedata, "type": "file"}
            self.users[recipient]["messages"].append(file_msg)
        return {"status": "success", "message": "File sent"}

    def get_messages(self, request):
        username = request.get("username")
        if not username:
            return {"status": "error", "message": "Username required"}
        with self.lock:
            if username not in self.users:
                return {"status": "error", "message": "User not found"}
            messages = self.users[username]["messages"]
            # Clear the inbox after retrieval.
            self.users[username]["messages"] = []
        return {"status": "success", "messages": messages}

if __name__ == "__main__":
    host = input("Enter server IP (e.g., 0.0.0.0): ").strip() or "0.0.0.0"
    port_input = input("Enter server port (e.g., 12345): ").strip()
    port = int(port_input) if port_input else 12345
    server = LegacyChatServer(host, port)
    server.start()
