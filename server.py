import socket
import threading
import json
import os
from settlement import minimize_cash_flow

HOST = "0.0.0.0"
PORT = 5005

# ------------------ File Path ------------------ #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")

# ------------------ Users ------------------ #
# Hardcoded users
USERS = {
    "dhruv": "1234",
    "abhisht": "xyz",
    "raghav": "panda123",
    "yashi": "23103038"
}

active_clients = {}
lock = threading.Lock()


# ------------------ Data Handling ------------------ #
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"groups": {}}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {"groups": {}}


def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print("[SAVE ERROR]:", e)


data_store = load_data()


# ------------------ Communication ------------------ #
def send(conn, msg):
    try:
        conn.sendall((json.dumps(msg) + "\n").encode())
    except:
        pass


def broadcast(group, message):
    for user in group["members"]:
        if user in active_clients:
            send(active_clients[user], message)


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
    password = req["data"].get("password", "")

    with lock:
        if group_name in data_store["groups"]:
            return {"status": "error", "message": "Group already exists"}

        data_store["groups"][group_name] = {
            "members": [user],
            "transactions": [],
            "password": password
        }

        save_data(data_store)

    return {"status": "ok", "message": "Group created successfully"}


def handle_join_group(req, user):
    group_name = req["data"]["group"]
    password = req["data"].get("password", "")

    with lock:
        if group_name not in data_store["groups"]:
            return {"status": "error", "message": "Group not found"}

        group = data_store["groups"][group_name]
        stored_password = group.get("password", "")

        if stored_password and stored_password != password:
            return {"status": "error", "message": "Invalid group password"}

        if user not in group["members"]:
            group["members"].append(user)

        save_data(data_store)

    return {"status": "ok", "message": "Joined group"}


def handle_list_groups(user):
    groups = [
        g for g in data_store["groups"]
        if user in data_store["groups"][g]["members"]
    ]
    return {"status": "ok", "groups": groups}


def handle_get_group_members(req, user):
    group_name = req["data"]["group"]

    if group_name not in data_store["groups"]:
        return {"status": "error", "message": "Group not found"}

    group = data_store["groups"][group_name]
    members = group.get("members", [])

    if user not in members:
        return {"status": "error", "message": "Not a member of this group"}

    return {"status": "ok", "members": members}


def handle_add_transaction(req, user):
    group_name = req["data"]["group"]
    amount = req["data"]["amount"]
    split_between = req["data"]["split_between"]
    include_payer = req["data"].get("include_payer", False)

    if group_name not in data_store["groups"]:
        return {"status": "error", "message": "Group not found"}

    group = data_store["groups"][group_name]
    members = group.get("members", [])

    all_people = split_between[:]
    if include_payer:
        all_people.append(user)

    for u in split_between:
        if u not in members:
            return {"status": "error", "message": f"{u} not in group"}

    txn = {
        "payer": user,
        "amount": amount,
        "split_between": split_between,
        "include_payer": include_payer
    }

    with lock:
        if "transactions" not in group:
            group["transactions"] = []
        group["transactions"].append(txn)
        save_data(data_store)

    broadcast(group, {
        "type": "notification",
        "message": f"{user} added ₹{amount} expense"
    })

    return {"status": "ok", "message": "Transaction added"}


def handle_view_transactions(req):
    group_name = req["data"]["group"]

    if group_name not in data_store["groups"]:
        return {"status": "error", "message": "Group not found"}

    return {
        "status": "ok",
        "transactions": data_store["groups"][group_name].get("transactions", [])
    }


def handle_delete_transaction(req):
    group_name = req["data"]["group"]
    index = req["data"]["index"]

    if group_name not in data_store["groups"]:
        return {"status": "error", "message": "Group not found"}

    group = data_store["groups"][group_name]
    transactions = group.get("transactions", [])

    with lock:
        try:
            transactions.pop(index)
            group["transactions"] = transactions
            save_data(data_store)
            return {"status": "ok", "message": "Transaction deleted"}
        except:
            return {"status": "error", "message": "Invalid index"}


# ------------------ Balance Logic ------------------ #

def compute_balances(group):
    members = group.get("members", [])
    transactions = group.get("transactions", [])
    balances = {member: 0 for member in members}

    for txn in transactions:
        payer = txn.get("payer")
        amount = txn.get("amount", 0)
        split = txn.get("split_between", [])
        include_payer = txn.get("include_payer", False)

        if payer not in balances:
            continue

        if not split:
            continue

        if include_payer:
            share = amount / (len(split) + 1)
            balances[payer] += amount - share
        else:
            balances[payer] += amount
            share = amount / len(split)

        for user in split:
            if user in balances:
                balances[user] -= share

    return balances


def handle_view_balances(req):
    group_name = req["data"]["group"]

    if group_name not in data_store["groups"]:
        return {"status": "error", "message": "Group not found"}

    group = data_store["groups"][group_name]
    balances = compute_balances(group)

    balances = {k: round(v, 2) for k, v in balances.items()}

    return {"status": "ok", "balances": balances}


# ------------------ Settlement ------------------ #

def handle_settle(req):
    try:
        group_name = req["data"]["group"]

        if group_name not in data_store["groups"]:
            return {"status": "error", "message": "Group not found"}

        group = data_store["groups"][group_name]
        members = group.get("members", [])
        transactions_list = group.get("transactions", [])

        if not transactions_list:
            return {"status": "ok", "settlements": []}

        participants = members
        transactions = []
        for txn in transactions_list:
            payer = txn.get("payer")
            amount = txn.get("amount", 0)
            split_between = txn.get("split_between", [])
            include_payer = txn.get("include_payer", False)

            if split_between:
                if include_payer:
                    share = amount / (len(split_between) + 1)
                    for person in split_between:
                        transactions.append((person, payer, share))
                else:
                    share = amount / len(split_between)
                    for person in split_between:
                        transactions.append((person, payer, share))

        settlements = minimize_cash_flow(participants, transactions)
        settlements = [
            {"from": s[0], "to": s[1], "amount": round(s[2], 2)}
            for s in settlements
        ]

        broadcast(group, {
            "type": "settlement",
            "data": settlements
        })

        return {"status": "ok", "settlements": settlements}

    except Exception as e:
        print("[SETTLE ERROR]:", e)
        return {"status": "error", "message": "Settlement failed"}


# ------------------ Client Handler ------------------ #

def handle_client(conn, addr):
    print(f"[CONNECTED] {addr}")
    user = None
    buffer = ""

    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break

            buffer += data.decode()

            while "\n" in buffer:
                msg, buffer = buffer.split("\n", 1)

                try:
                    req = json.loads(msg)
                except:
                    continue

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

                elif action == "get_group_members":
                    res = handle_get_group_members(req, user)

                elif action == "add_transaction":
                    res = handle_add_transaction(req, user)

                elif action == "view_transactions":
                    res = handle_view_transactions(req)

                elif action == "delete_transaction":
                    res = handle_delete_transaction(req)

                elif action == "view_balances":
                    res = handle_view_balances(req)

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
