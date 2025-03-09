#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext, filedialog
import threading
import socket
import json
import time
import base64
import os

# Default server details (will ask at startup)
SERVER_IP = "127.0.0.1"
SERVER_PORT = 12345

def send_request(request):
    """
    Opens a new socket connection, sends JSON (terminated by a newline), and waits for a JSON reply.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((SERVER_IP, SERVER_PORT))
            s.sendall((json.dumps(request) + "\n").encode("utf-8"))
            data = ""
            while "\n" not in data:
                chunk = s.recv(4096).decode("utf-8")
                if not chunk:
                    break
                data += chunk
            return json.loads(data.strip())
    except Exception as e:
        return {"status": "error", "message": str(e)}

class LegacyChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LegacyChat")
        self.username = None
        self.buddies = {}     # buddy_username -> buddy_name mapping
        # chat_windows holds tuples: (chat_window, display_widget, entry_widget)
        self.chat_windows = {}
        self.create_login_signup()

    def create_login_signup(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        frame = tk.Frame(self.root)
        frame.pack(pady=20)
        tk.Label(frame, text="Welcome to LegacyChat", font=('Helvetica', 16)).pack(pady=10)
        tk.Button(frame, text="Sign Up", command=self.signup_window, width=20).pack(pady=5)
        tk.Button(frame, text="Log In", command=self.login_window, width=20).pack(pady=5)

    def signup_window(self):
        signup_win = tk.Toplevel(self.root)
        signup_win.title("Sign Up")
        tk.Label(signup_win, text="Username:").grid(row=0, column=0, padx=5, pady=5)
        username_entry = tk.Entry(signup_win)
        username_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(signup_win, text="Password:").grid(row=1, column=0, padx=5, pady=5)
        password_entry = tk.Entry(signup_win, show="*")
        password_entry.grid(row=1, column=1, padx=5, pady=5)
        def attempt_signup():
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            if not username or not password:
                messagebox.showerror("Error", "Username and password required.")
                return
            response = send_request({"action": "signup", "username": username, "password": password})
            if response.get("status") == "success":
                messagebox.showinfo("Success", "Signup successful! Logging in...")
                signup_win.destroy()
                self.username = username
                self.open_buddy_list()
            else:
                messagebox.showerror("Error", response.get("message"))
        tk.Button(signup_win, text="Sign Up", command=attempt_signup).grid(row=2, columnspan=2, pady=10)

    def login_window(self):
        login_win = tk.Toplevel(self.root)
        login_win.title("Log In")
        tk.Label(login_win, text="Username:").grid(row=0, column=0, padx=5, pady=5)
        username_entry = tk.Entry(login_win)
        username_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(login_win, text="Password:").grid(row=1, column=0, padx=5, pady=5)
        password_entry = tk.Entry(login_win, show="*")
        password_entry.grid(row=1, column=1, padx=5, pady=5)
        def attempt_login():
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            if not username or not password:
                messagebox.showerror("Error", "Username and password required.")
                return
            response = send_request({"action": "login", "username": username, "password": password})
            if response.get("status") == "success":
                messagebox.showinfo("Success", "Login successful!")
                login_win.destroy()
                self.username = username
                buddies = response.get("buddies", [])
                for buddy in buddies:
                    self.buddies[buddy] = buddy  # default: buddy name same as username
                self.open_buddy_list()
            else:
                messagebox.showerror("Error", response.get("message"))
        tk.Button(login_win, text="Log In", command=attempt_login).grid(row=2, columnspan=2, pady=10)

    def open_buddy_list(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        frame = tk.Frame(self.root)
        frame.pack(pady=20)
        tk.Label(frame, text=f"Buddy List ({self.username})", font=('Helvetica', 16)).pack(pady=10)
        list_frame = tk.Frame(frame)
        list_frame.pack(pady=10)
        # Create a button for each buddy that opens the chat window
        for buddy_username, buddy_name in self.buddies.items():
            btn = tk.Button(list_frame, text=buddy_name, width=20,
                            command=lambda bu=buddy_username: self.open_chat(bu))
            btn.pack(pady=5)
        tk.Button(frame, text="Add Buddie", command=self.add_buddy_window, width=20).pack(pady=5)
        # Start a global polling thread that collects incoming messages
        self.start_polling()

    def add_buddy_window(self):
        add_win = tk.Toplevel(self.root)
        add_win.title("Add Buddie")
        tk.Label(add_win, text="Buddy Username:").grid(row=0, column=0, padx=5, pady=5)
        buddy_username_entry = tk.Entry(add_win)
        buddy_username_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(add_win, text="Buddy Name:").grid(row=1, column=0, padx=5, pady=5)
        buddy_name_entry = tk.Entry(add_win)
        buddy_name_entry.grid(row=1, column=1, padx=5, pady=5)
        def attempt_add():
            buddy_username = buddy_username_entry.get().strip()
            buddy_name = buddy_name_entry.get().strip()
            if not buddy_username or not buddy_name:
                messagebox.showerror("Error", "Please fill all fields.")
                return
            response = send_request({
                "action": "add_buddy",
                "username": self.username,
                "buddy_username": buddy_username,
                "buddy_name": buddy_name
            })
            if response.get("status") == "success":
                messagebox.showinfo("Success", "Buddy added!")
                self.buddies[buddy_username] = buddy_name
                add_win.destroy()
                self.open_buddy_list()  # refresh list
            else:
                messagebox.showerror("Error", response.get("message"))
        tk.Button(add_win, text="Add", command=attempt_add).grid(row=2, columnspan=2, pady=10)

    def open_chat(self, buddy_username):
        # If the chat window is already open, bring it to front.
        if buddy_username in self.chat_windows:
            window, display, entry = self.chat_windows[buddy_username]
            window.lift()
            return
        chat_win = tk.Toplevel(self.root)
        chat_win.title(f"Chat with {self.buddies.get(buddy_username, buddy_username)}")
        display = scrolledtext.ScrolledText(chat_win, width=50, height=20, state="disabled")
        display.pack(pady=5)
        # Input frame holds the text entry and three buttons: Emoji, Send File, and Send.
        input_frame = tk.Frame(chat_win)
        input_frame.pack(pady=5)
        entry = tk.Entry(input_frame, width=40)
        entry.grid(row=0, column=0, padx=5)
        btn_emoji = tk.Button(input_frame, text="Emoji", command=lambda: self.emoji_picker(entry))
        btn_emoji.grid(row=0, column=1, padx=5)
        btn_send_file = tk.Button(input_frame, text="Send File", command=lambda: self.send_file_message(buddy_username, display, entry))
        btn_send_file.grid(row=0, column=2, padx=5)
        btn_send = tk.Button(input_frame, text="Send", command=lambda: self.send_msg(buddy_username, display, entry))
        btn_send.grid(row=0, column=3, padx=5)

        self.chat_windows[buddy_username] = (chat_win, display, entry)
        chat_win.protocol("WM_DELETE_WINDOW", lambda: self.close_chat(buddy_username))

    def close_chat(self, buddy_username):
        if buddy_username in self.chat_windows:
            window, display, entry = self.chat_windows[buddy_username]
            window.destroy()
            del self.chat_windows[buddy_username]

    def send_msg(self, buddy_username, display, entry):
        msg = entry.get().strip()
        if not msg:
            return
        response = send_request({
            "action": "send_message",
            "sender": self.username,
            "recipient": buddy_username,
            "message": msg
        })
        if response.get("status") == "success":
            self.append_chat(display, f"You: {msg}\n")
            entry.delete(0, tk.END)
        else:
            messagebox.showerror("Error", response.get("message"))

    def send_file_message(self, buddy_username, display, entry):
        file_path = filedialog.askopenfilename()
        if not file_path:
            return
        try:
            with open(file_path, "rb") as f:
                file_data = f.read()
            b64data = base64.b64encode(file_data).decode("utf-8")
            filename = os.path.basename(file_path)
            response = send_request({
                "action": "send_file",
                "sender": self.username,
                "recipient": buddy_username,
                "filename": filename,
                "filedata": b64data
            })
            if response.get("status") == "success":
                self.append_chat(display, f"You sent file: {filename}\n")
                entry.delete(0, tk.END)
            else:
                messagebox.showerror("Error", response.get("message"))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def emoji_picker(self, entry_widget):
        picker = tk.Toplevel(self.root)
        picker.title("Emoji Picker")
        # A small set of common emojis.
        emojis = ["😊", "😂", "😍", "😢", "😎", "👍", "🙌", "🔥"]
        row = 0
        col = 0
        for emoji in emojis:
            btn = tk.Button(picker, text=emoji, command=lambda e=emoji: self.insert_emoji(entry_widget, e))
            btn.grid(row=row, column=col, padx=5, pady=5)
            col += 1
            if col >= 4:
                col = 0
                row += 1

    def insert_emoji(self, entry_widget, emoji):
        entry_widget.insert(tk.END, emoji)

    def append_chat(self, display, message):
        display.config(state="normal")
        display.insert(tk.END, message)
        display.config(state="disabled")
        display.see(tk.END)

    def start_polling(self):
        thread = threading.Thread(target=self.global_poll_messages, daemon=True)
        thread.start()

    def global_poll_messages(self):
        """
        Continuously polls the server for incoming messages.
        For each retrieved message, schedules a UI callback on the main thread.
        """
        while True:
            time.sleep(1)
            response = send_request({"action": "get_messages", "username": self.username})
            if response.get("status") == "success":
                messages = response.get("messages", [])
                for msg in messages:
                    buddy_username = msg.get("from")
                    self.root.after(0, self.handle_incoming_message, buddy_username, msg)

    def handle_incoming_message(self, buddy_username, msg):
        buddy_name = self.buddies.get(buddy_username, buddy_username)
        # If the message holds a 'type' field and it equals 'file', process as file.
        if msg.get("type") == "file":
            if buddy_username in self.chat_windows:
                window, display, entry = self.chat_windows[buddy_username]
                self.append_chat(display, f"{buddy_name} sent a file: {msg.get('filename')}\n")
                # Prompt the user to save the received file.
                self.prompt_save_file(buddy_name, msg.get("filename"), msg.get("filedata"))
            else:
                self.push_notification(buddy_username, f"{buddy_name} sent a file: {msg.get('filename')}")
        else:
            # Process as a standard text message.
            if buddy_username in self.chat_windows:
                window, display, entry = self.chat_windows[buddy_username]
                self.append_chat(display, f"{buddy_name}: {msg.get('message')}\n")
            else:
                self.push_notification(buddy_username, f"New message from {buddy_name}")

    def push_notification(self, buddy_username, text):
        """
        Creates a transient popup notification to alert the user of new messages.
        """
        notif = tk.Toplevel(self.root)
        notif.title("New Message")
        notif.geometry("250x100")
        tk.Label(notif, text=text, font=('Helvetica', 12)).pack(expand=True)
        # Auto-destroy the popup after 3 seconds.
        notif.after(3000, notif.destroy)

    def prompt_save_file(self, buddy_name, filename, filedata):
        """
        Prompts the user to save an incoming file.
        """
        if messagebox.askyesno("File Received", f"{buddy_name} sent file: {filename}. Save now?"):
            save_path = filedialog.asksaveasfilename(initialfile=filename)
            if save_path:
                try:
                    with open(save_path, 'wb') as f:
                        f.write(base64.b64decode(filedata))
                    messagebox.showinfo("Saved", "File saved successfully!")
                except Exception as e:
                    messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    s_ip = simpledialog.askstring("Server IP", "Enter server IP:", initialvalue=SERVER_IP)
    s_port = simpledialog.askinteger("Server Port", "Enter server port:", initialvalue=SERVER_PORT)
    if s_ip:
        SERVER_IP = s_ip
    if s_port:
        SERVER_PORT = s_port
    app = LegacyChatApp(root)
    root.mainloop()
