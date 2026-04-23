import socket
import threading
import json
import os
from settlement import minimize_cash_flow

HOST = "0.0.0.0"
PORT = 5000
DATA_FILE = "data.json"

# Hardcoded users
USERS = {
    "dhruv": "1234",
    "abhisht": "xyz",
    "raghav": "panda123",
    "yashi": "23103038"
}

# Active connections {username: conn}
active_clients = {}

lock = threading.Lock()


# ------------------ Data Handling ------------------ #
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"groups": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


data_store = load_data()


# ------------------ Utility ------------------ #
def send(conn, msg):
    conn.sendall((json.dumps(msg) + "\n").encode())


def broadcast(group, message):
    for user in group["members"]:
        if user in active_clients:
            try:
                send(active_clients[user], message)
            except:
                pass


# ------------------ Core Logic ------------------ #

def handle_login(conn, req):
    username = req["data"]["username"]
    password = req["data"]["password"]

    if username in USERS and USERS[username] == password:
        active_clients[username] = conn
        return {"status": "ok", "message": "Login successful"}
    return {"status": "error", "message": "Invalid credentials"}


def handle_create_group(req, user):
    group_name = req["data"]["group"]

    with lock:
        if group_name in data_store["groups"]:
            return {"status": "error", "message": "Group exists"}

        data_store["groups"][group_name] = {
            "members": [user],
            "transactions": []
        }
        save_data(data_store)

    return {"status": "ok", "message": "Group created"}


def handle_join_group(req, user):
    group_name = req["data"]["group"]

    with lock:
        if group_name not in data_store["groups"]:
            return {"status": "error", "message": "Group not found"}

        if user not in data_store["groups"][group_name]["members"]:
            data_store["groups"][group_name]["members"].append(user)

        save_data(data_store)

    return {"status": "ok", "message": "Joined group"}


def handle_list_groups(user):
    groups = [
        g for g in data_store["groups"]
        if user in data_store["groups"][g]["members"]
    ]
    return {"status": "ok", "groups": groups}


def handle_add_transaction(req, user):
    group = req["data"]["group"]
    amount = req["data"]["amount"]
    split_between = req["data"]["split_between"]

    txn = {
        "payer": user,
        "amount": amount,
        "split_between": split_between
    }

    with lock:
        data_store["groups"][group]["transactions"].append(txn)
        save_data(data_store)

    broadcast(data_store["groups"][group], {
        "type": "notification",
        "message": f"{user} added a transaction"
    })

    return {"status": "ok", "message": "Transaction added"}


def handle_view_transactions(req):
    group = req["data"]["group"]
    txns = data_store["groups"][group]["transactions"]
    return {"status": "ok", "transactions": txns}


def handle_delete_transaction(req):
    group = req["data"]["group"]
    index = req["data"]["index"]

    with lock:
        try:
            data_store["groups"][group]["transactions"].pop(index)
            save_data(data_store)
            return {"status": "ok", "message": "Deleted"}
        except:
            return {"status": "error", "message": "Invalid index"}


def compute_balances(group):
    balances = {}

    for member in group["members"]:
        balances[member] = 0

    for txn in group["transactions"]:
        payer = txn["payer"]
        amount = txn["amount"]
        split = txn["split_between"]

        share = amount / (len(split) + 1)

        balances[payer] += amount - share

        for user in split:
            balances[user] -= share

    return balances


def handle_settle(req):
    group_name = req["data"]["group"]
    group = data_store["groups"][group_name]

    balances = compute_balances(group)
    settlements = minimize_cash_flow(balances)

    message = {
        "type": "settlement",
        "data": settlements
    }

    broadcast(group, message)

    return {"status": "ok", "settlements": settlements}


# ------------------ Client Handler ------------------ #

def handle_client(conn, addr):
    print(f"[CONNECTED] {addr}")
    user = None

    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break

            req = json.loads(data.decode())
            action = req.get("action")

            if action == "login":
                res = handle_login(conn, req)
                if res["status"] == "ok":
                    user = req["data"]["username"]

            elif action == "create_group":
                res = handle_create_group(req, user)

            elif action == "join_group":
                res = handle_join_group(req, user)

            elif action == "list_groups":
                res = handle_list_groups(user)

            elif action == "add_transaction":
                res = handle_add_transaction(req, user)

            elif action == "view_transactions":
                res = handle_view_transactions(req)

            elif action == "delete_transaction":
                res = handle_delete_transaction(req)

            elif action == "settle":
                res = handle_settle(req)

            else:
                res = {"status": "error", "message": "Unknown action"}

            send(conn, res)

    except Exception as e:
        print("[ERROR]", e)

    finally:
        if user in active_clients:
            del active_clients[user]
        conn.close()
        print(f"[DISCONNECTED] {addr}")


# ------------------ Start Server ------------------ #

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()

    print(f"[SERVER STARTED] {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()


if __name__ == "__main__":
    start_server()
