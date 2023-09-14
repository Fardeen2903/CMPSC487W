import tkinter as tk
from tkinter import ttk
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

cred = credentials.Certificate("serviceKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

# Define a global variable to track the current user's entry status
current_entry_status = {}

# Function to log access
def log_access(user_id):
    timestamp = datetime.now()

    if user_id in current_entry_status:
        # This user has already checked in, so this card swipe is for exit
        entry_time = current_entry_status[user_id]
        exit_time = timestamp

        # Update the access data with entry and exit times
        access_data = {
            "ID": user_id,
            "IN": entry_time,
            "OUT": exit_time,
            "Status": "Exited",  # Assuming non-admin user
        }

        # Remove the user from the current entry status tracking
        del current_entry_status[user_id]

    else:
        # This is a new entry for the user
        current_entry_status[user_id] = timestamp

        # Create an access record for entry
        access_data = {
            "ID": user_id,
            "IN": timestamp,
            "OUT": None,  # Initialize exit_time as None
            "Status": "Entered",  # Assuming non-admin user
        }

    # Add the access data to the "Logs" collection in Firestore
    db.collection("Logs").add(access_data)
    status_label.config(text="Access recorded")

# Function to browse access history with time filter
def browse_access_history():
    user_id = int(user_id_entry.get())
    start_time = start_time_entry.get()
    end_time = end_time_entry.get()

    # Check if start_time and end_time are provided
    if start_time and end_time:
        # Convert the timestamp strings to datetime objects
        start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
        end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M")

        # Query access history within the specified time range
        access_ref = db.collection("Logs").where("ID", "==", user_id) \
            .where("IN", ">=", start_time) \
            .where("IN", "<=", end_time) \
            .stream()
    else:
        # Query access history without time filter
        access_ref = db.collection("Logs").where("ID", "==", user_id).stream()

    history_text.config(state="normal")
    history_text.delete("1.0", tk.END)  # Clear existing text
    for doc in access_ref:
        data = doc.to_dict()
        timestamp = data.get("IN", "")
        status = data.get("Status", "")
        history_text.insert(tk.END, f"Timestamp: {timestamp}\nStatus: {status}\n\n")
    history_text.config(state="disabled")

# Function to toggle ban/unban user
def toggle_ban(user_id):
    access_ref = db.collection("users").where("ID", "==", user_id).stream()
    for doc in access_ref:
        doc_ref = db.collection("users").document(doc.id)
        doc_data = doc.to_dict()
        status = doc_data.get("Status", "Active")
        new_status = "Banned" if status == "Active" else "Active"
        doc_ref.update({"Status": new_status})

# Function to open the admin window and display the "Users" collection
def admin_access():
    admin_id = int(user_id_entry.get())  # Prompt for admin ID
    admin_ref = db.collection("users").where("ID", "==", int(admin_id)).stream()
    is_admin = False

    for doc in admin_ref:
        doc_data = doc.to_dict()
        admin_status = doc_data.get("Admin", "")
        if admin_status == True:
            is_admin = True
            break

    if is_admin:
        admin_window = tk.Toplevel()
        admin_window.title("Admin Access")
        # Enable the ban/unban button after successful admin access
        ban_button.config(state="normal")
        # Enable the filter button after successful admin access
        filter_button.config(state="normal")

        # Create a treeview to display the "Users" collection
        user_tree = ttk.Treeview(admin_window, columns=("ID", "Name", "Admin", "Banned"))
        user_tree.heading("#1", text="ID")
        user_tree.heading("#2", text="Name")
        user_tree.heading("#3", text="Admin")
        user_tree.heading("#4", text="Banned")
        user_tree.pack()

        # Create a function to populate the treeview with data from "Users" collection
        def populate_treeview():
            user_tree.delete(*user_tree.get_children())
            users_ref = db.collection("users").stream()
            for doc in users_ref:
                data = doc.to_dict()
                user_id = data.get("ID", "")
                user_name = data.get("Name", "")
                user_status = data.get("Admin", "")
                user_ban = data.get("Ban", "")
                user_tree.insert("", "end", values=(user_id, user_name, user_status, user_ban))

        # Create a button to refresh the treeview data
        refresh_button = tk.Button(admin_window, text="Refresh", command=populate_treeview)
        refresh_button.pack()

        # Create a function to display user's access history when clicked
        def display_access_history(event):
            item = user_tree.selection()[0]
            user_id = user_tree.item(item, "values")[0]
            access_history_window = tk.Toplevel()
            access_history_window.title(f"Access History for User {user_id}")

            # Create a treeview to display the timestamps and entry/exit status
            history_tree = ttk.Treeview(access_history_window, columns=("Timestamp", "Status"))
            history_tree.heading("#1", text="Timestamp")
            history_tree.heading("#2", text="Status")
            history_tree.pack()

            access_ref = db.collection("Logs").where("ID", "==", int(user_id)).stream()
            for doc in access_ref:
                data = doc.to_dict()
                timestamp = data.get("IN", "")
                status = data.get("Status", "")
                history_tree.insert("", "end", values=(timestamp, status))

        user_tree.bind("<Double-1>", display_access_history)

        # Initially populate the treeview
        populate_treeview()
    else:
        print("Invalid Access: Not an admin")

    user_tree.bind("<Double-1>", display_access_history)

    # Initially populate the treeview
    populate_treeview()

# Create the main application window
app = tk.Tk()
app.title("SUN Lab Access System")

# Create and place GUI elements
user_id_label = tk.Label(app, text="Admin User ID:")
user_id_label.pack()

user_id_entry = tk.Entry(app)
user_id_entry.pack()

log_button = tk.Button(app, text="Log Access", command=lambda: log_access(int(user_id_entry.get())))
log_button.pack()

history_text = tk.Text(app, height=10, width=40, state="disabled")
history_text.pack()

start_time_label = tk.Label(app, text="Start Time (YYYY-MM-DD HH:MM:SS):")
start_time_label.pack()

start_time_entry = tk.Entry(app)
start_time_entry.pack()

end_time_label = tk.Label(app, text="End Time (YYYY-MM-DD HH:MM:SS):")
end_time_label.pack()

end_time_entry = tk.Entry(app)
end_time_entry.pack()

# Initially disable the filter button
filter_button = tk.Button(app, text="Apply Filter", command=browse_access_history, state="disabled")
filter_button.pack()

status_label = tk.Label(app, text="")
status_label.pack()

# Initially disable the ban/unban button
ban_button = tk.Button(app, text="Toggle Ban/Unban", command=lambda: toggle_ban(int(user_id_entry.get())), state="disabled")
ban_button.pack()

admin_access_button = tk.Button(app, text="Admin Access", command=admin_access)
admin_access_button.pack()

app.mainloop()

