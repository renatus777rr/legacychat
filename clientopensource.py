#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext, filedialog
import threading
import socket
import json
import time
import base64
import os

# Default server details
SERVER_IP = "127.0.0.1"
SERVER_PORT = 12345

def send_request(request):
    """
    Opens a new socket connection, sends JSON (terminated by a newline),
    and waits for a JSON reply.
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
        # Set a light blue background reminiscent of MSN Messenger
        self.root.configure(bg="#E7F3FF")
        self.username = None
        self.current_status = "online"
        # buddies: mapping buddy_username -> buddy_name
        self.buddies = {}
        # buddy_buttons: mapping buddy_username -> associated Tkinter Button widget for status updating
        self.buddy_buttons = {}
        # chat_windows: mapping buddy_username -> (window, display_widget, entry_widget)
        self.chat_windows = {}
        self.create_login_signup()

    def create_menu_bar(self):
        menu_bar = tk.Menu(self.root)
        account_menu = tk.Menu(menu_bar, tearoff=0)
        account_menu.add_command(label="Online", command=lambda: self.update_status("online"))
        account_menu.add_command(label="Busy", command=lambda: self.update_status("busy"))
        account_menu.add_command(label="Away", command=lambda: self.update_status("away"))
        account_menu.add_command(label="Offline", command=lambda: self.update_status("offline"))
        menu_bar.add_cascade(label=self.username, menu=account_menu)
        self.root.config(menu=menu_bar)

    def update_status(self, new_status):
        res = send_request({
            "action": "update_status",
            "username": self.username,
            "status": new_status
        })
        if res.get("status") == "success":
            self.current_status = new_status
            messagebox.showinfo("Status Updated", f"Your status is now: {new_status}")
            self.refresh_buddy_statuses()
        else:
            messagebox.showerror("Error", res.get("message"))

    def refresh_buddy_statuses(self):
        """
        Refresh each buddy's button text to include their current status.
        Schedules itself to run every 5 seconds.
        """
        for buddy_username, btn in self.buddy_buttons.items():
            res = send_request({
                "action": "get_buddy_status",
                "username": self.username,
                "buddy_username": buddy_username
            })
            if res.get("status") == "success":
                buddy_status = res.get("buddy_status", "offline")
            else:
                buddy_status = "unknown"
            buddy_name = self.buddies.get(buddy_username, buddy_username)
            btn.config(text=f"{buddy_name} ({buddy_status})")
        self.root.after(5000, self.refresh_buddy_statuses)

    def create_login_signup(self):
        # Clear any widgets from the root.
        for widget in self.root.winfo_children():
            widget.destroy()
        frame = tk.Frame(self.root, bg="#E7F3FF")
        frame.pack(pady=20)
        tk.Label(frame, text="Welcome to LegacyChat", font=("Segoe UI", 16), bg="#E7F3FF").pack(pady=10)
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
                messagebox.showerror("Error", "Username and password required")
                return
            res = send_request({"action": "signup", "username": username, "password": password})
            if res.get("status") == "success":
                messagebox.showinfo("Success", "Signup successful! Logging in...")
                signup_win.destroy()
                self.username = username
                self.open_buddy_list()
            else:
                messagebox.showerror("Error", res.get("message"))
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
                messagebox.showerror("Error", "Username and password required")
                return
            res = send_request({"action": "login", "username": username, "password": password})
            if res.get("status") == "success":
                messagebox.showinfo("Success", "Login successful!")
                login_win.destroy()
                self.username = username
                buddies = res.get("buddies", [])
                for buddy in buddies:
                    self.buddies[buddy["username"]] = buddy["name"]
                self.open_buddy_list()
            else:
                messagebox.showerror("Error", res.get("message"))
        tk.Button(login_win, text="Log In", command=attempt_login).grid(row=2, columnspan=2, pady=10)

    def open_buddy_list(self):
        # Clear the root.
        for widget in self.root.winfo_children():
            widget.destroy()
        self.create_menu_bar()
        frame = tk.Frame(self.root, bg="#E7F3FF")
        frame.pack(pady=20)
        tk.Label(frame, text=f"Buddy List ({self.username})", font=("Segoe UI", 16), bg="#E7F3FF").pack(pady=10)
        list_frame = tk.Frame(frame, bg="#E7F3FF")
        list_frame.pack(pady=10)
        self.buddy_buttons = {}
        for buddy_username, buddy_name in self.buddies.items():
            btn = tk.Button(list_frame, text=buddy_name, width=25,
                            command=lambda bu=buddy_username: self.open_chat(bu))
            btn.pack(pady=5)
            self.buddy_buttons[buddy_username] = btn
        tk.Button(frame, text="Add Buddie", command=self.add_buddy_window, width=20).pack(pady=5)
        # Start polling for new messages and refreshing buddy statuses.
        self.start_polling()
        self.refresh_buddy_statuses()

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
            res = send_request({
                "action": "add_buddy",
                "username": self.username,
                "buddy_username": buddy_username,
                "buddy_name": buddy_name
            })
            if res.get("status") == "success":
                messagebox.showinfo("Success", "Buddy added!")
                self.buddies[buddy_username] = buddy_name
                add_win.destroy()
                self.open_buddy_list()  # refresh list
            else:
                messagebox.showerror("Error", res.get("message"))
        tk.Button(add_win, text="Add", command=attempt_add).grid(row=2, columnspan=2, pady=10)

    def open_chat(self, buddy_username):
        if buddy_username in self.chat_windows:
            window, display, entry = self.chat_windows[buddy_username]
            window.lift()
            return
        # Create a chat window that mimics the classic MSN Messenger style.
        chat_win = tk.Toplevel(self.root)
        chat_win.geometry("500x400")
        
        # Header area similar to WLM with a blue title bar.
        header_frame = tk.Frame(chat_win, bg="#2C82C9")
        header_frame.pack(fill="x")
        header_label = tk.Label(header_frame, text=f"Chat with {self.buddies.get(buddy_username, buddy_username)}",
                                bg="#2C82C9", fg="white", font=("Segoe UI", 10, "bold"))
        header_label.pack(padx=10, pady=5, side="left")
        close_btn = tk.Button(header_frame, text="X", bg="#E74C3C", fg="white",
                              command=lambda: self.close_chat(buddy_username))
        close_btn.pack(padx=10, pady=5, side="right")
        
        # Chat display area.
        display = scrolledtext.ScrolledText(chat_win, width=50, height=15, state="disabled",
                                              font=("Segoe UI", 10))
        display.pack(pady=5)
        # Input frame: includes our entry and several MSN-style buttons.
        input_frame = tk.Frame(chat_win)
        input_frame.pack(pady=5)
        entry = tk.Entry(input_frame, width=40, font=("Segoe UI", 10))
        entry.grid(row=0, column=0, padx=5)
        btn_emoji = tk.Button(input_frame, text="Emoji", command=lambda: self.emoji_picker(entry))
        btn_emoji.grid(row=0, column=1, padx=5)
        btn_send_file = tk.Button(input_frame, text="Send File",
                                  command=lambda: self.send_file_message(buddy_username, display, entry))
        btn_send_file.grid(row=0, column=2, padx=5)
        # New MSN-style buttons: Nudge and Wink.
        btn_nudge = tk.Button(input_frame, text="Nudge",
                              command=lambda: self.send_nudge(buddy_username, display))
        btn_nudge.grid(row=0, column=3, padx=5)
        btn_wink = tk.Button(input_frame, text="Wink",
                             command=lambda: self.send_wink(buddy_username, display))
        btn_wink.grid(row=0, column=4, padx=5)
        btn_send = tk.Button(input_frame, text="Send",
                             command=lambda: self.send_msg(buddy_username, display, entry))
        btn_send.grid(row=0, column=5, padx=5)
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
        res = send_request({
            "action": "send_message",
            "sender": self.username,
            "recipient": buddy_username,
            "message": msg
        })
        if res.get("status") == "success":
            self.append_chat(display, f"You: {msg}\n")
            entry.delete(0, tk.END)
        else:
            messagebox.showerror("Error", res.get("message"))

    def send_file_message(self, buddy_username, display, entry):
        file_path = filedialog.askopenfilename()
        if not file_path:
            return
        try:
            with open(file_path, "rb") as f:
                file_data = f.read()
            b64data = base64.b64encode(file_data).decode("utf-8")
            filename = os.path.basename(file_path)
            res = send_request({
                "action": "send_file",
                "sender": self.username,
                "recipient": buddy_username,
                "filename": filename,
                "filedata": b64data
            })
            if res.get("status") == "success":
                self.append_chat(display, f"You sent file: {filename}\n")
                entry.delete(0, tk.END)
            else:
                messagebox.showerror("Error", res.get("message"))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def emoji_picker(self, entry_widget):
        picker = tk.Toplevel(self.root)
        picker.title("Emoji Picker")
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

    def send_nudge(self, buddy_username, display):
        res = send_request({
            "action": "send_message",
            "sender": self.username,
            "recipient": buddy_username,
            "message": "[Nudge]",
            "type": "nudge"
        })
        if res.get("status") == "success":
            self.append_chat(display, "You nudged.\n")
        else:
            messagebox.showerror("Error", res.get("message"))

    def send_wink(self, buddy_username, display):
        res = send_request({
            "action": "send_message",
            "sender": self.username,
            "recipient": buddy_username,
            "message": "[Wink]",
            "type": "wink"
        })
        if res.get("status") == "success":
            self.append_chat(display, "You winked.\n")
        else:
            messagebox.showerror("Error", res.get("message"))

    def shake_window(self, window, count=0, original_coords=None):
        """
        Shakes the given window horizontally for a nudge/wink effect.
        """
        if original_coords is None:
            original_coords = (window.winfo_x(), window.winfo_y())
        if count < 10:
            offset = 10 if count % 2 == 0 else -10
            new_x = original_coords[0] + offset
            new_y = original_coords[1]
            window.geometry(f"+{new_x}+{new_y}")
            window.after(50, lambda: self.shake_window(window, count+1, original_coords))
        else:
            window.geometry(f"+{original_coords[0]}+{original_coords[1]}")

    def nudge_received(self, buddy_username):
        """
        Called when a nudge is received. If a chat window is open, shake it; else, show a notification.
        """
        buddy_name = self.buddies.get(buddy_username, buddy_username)
        if buddy_username in self.chat_windows:
            window, display, entry = self.chat_windows[buddy_username]
            self.shake_window(window)
            self.append_chat(display, f"{buddy_name} sent you a nudge!\n")
        else:
            self.push_notification(buddy_username, f"{buddy_name} sent you a nudge!")

    def wink_received(self, buddy_username):
        """
        Called when a wink is received.
        """
        buddy_name = self.buddies.get(buddy_username, buddy_username)
        if buddy_username in self.chat_windows:
            window, display, entry = self.chat_windows[buddy_username]
            self.append_chat(display, f"{buddy_name} sent you a wink!\n")
            self.shake_window(window)
        else:
            self.push_notification(buddy_username, f"{buddy_name} sent you a wink!")

    def global_poll_messages(self):
        """
        Polls the server every second for new messages.
        Each retrieved message is scheduled on the main thread.
        """
        while True:
            time.sleep(1)
            res = send_request({"action": "get_messages", "username": self.username})
            if res.get("status") == "success":
                messages = res.get("messages", [])
                for msg in messages:
                    buddy_username = msg.get("from")
                    self.root.after(0, self.handle_incoming_message, buddy_username, msg)

    def handle_incoming_message(self, buddy_username, msg):
        buddy_name = self.buddies.get(buddy_username, buddy_username)
        msg_type = msg.get("type", "text")
        if msg_type == "file":
            if buddy_username in self.chat_windows:
                window, display, entry = self.chat_windows[buddy_username]
                self.append_chat(display, f"{buddy_name} sent a file: {msg.get('filename')}\n")
                self.prompt_save_file(buddy_name, msg.get("filename"), msg.get("filedata"))
            else:
                self.push_notification(buddy_username, f"{buddy_name} sent a file: {msg.get('filename')}")
        elif msg_type == "nudge":
            self.nudge_received(buddy_username)
        elif msg_type == "wink":
            self.wink_received(buddy_username)
        else:
            if buddy_username in self.chat_windows:
                window, display, entry = self.chat_windows[buddy_username]
                self.append_chat(display, f"{buddy_name}: {msg.get('message')}\n")
            else:
                self.push_notification(buddy_username, f"New message from {buddy_name}")

    def push_notification(self, buddy_username, text):
        notif = tk.Toplevel(self.root)
        notif.title("New Message")
        notif.geometry("250x100")
        tk.Label(notif, text=text, font=("Segoe UI", 12)).pack(expand=True)
        notif.after(3000, notif.destroy)

    def prompt_save_file(self, buddy_name, filename, filedata):
        if messagebox.askyesno("File Received", f"{buddy_name} sent file: {filename}. Save now?"):
            save_path = filedialog.asksaveasfilename(initialfile=filename)
            if save_path:
                try:
                    with open(save_path, "wb") as f:
                        f.write(base64.b64decode(filedata))
                    messagebox.showinfo("Saved", "File saved successfully!")
                except Exception as e:
                    messagebox.showerror("Error", str(e))

    def start_polling(self):
        thread = threading.Thread(target=self.global_poll_messages, daemon=True)
        thread.start()

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
