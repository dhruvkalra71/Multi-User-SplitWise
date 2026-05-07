import socket
import threading
import json
from queue import Queue

HOST = "127.0.0.1"
PORT = 5005

response_queue = Queue()


# ------------------ Send ------------------ #
def send(sock, msg):
    sock.sendall((json.dumps(msg) + "\n").encode())


# ------------------ Listener ------------------ #
def listen_server(sock):
    buffer = ""

    while True:
        try:
            data = sock.recv(4096)
            if not data:
                break

            buffer += data.decode()

            while "\n" in buffer:
                msg, buffer = buffer.split("\n", 1)
                res = json.loads(msg)

                # Notifications
                if res.get("type") == "notification":
                    print(f"\n🔔 {res['message']}")

                elif res.get("type") == "settlement":
                    print("\n💸 Settlement Suggestions:")
                    for s in res["data"]:
                        print(f"{s['from']} → {s['to']} : ₹{s['amount']}")

                else:
                    response_queue.put(res)

        except:
            break


# ------------------ Receive ------------------ #
def receive():
    return response_queue.get()


# ------------------ Pretty Print ------------------ #
def print_response(res):
    if not res:
        print("⚠️ No response")
        return

    if res.get("status") == "ok":
        if "message" in res:
            print(f"✅ {res['message']}")
        elif "groups" in res:
            print("\n📂 Your Groups:")
            if res["groups"]:
                for g in res["groups"]:
                    print(f"- {g}")
            else:
                print("No groups found")
    else:
        print(f"❌ {res.get('message', 'Error')}")


# ------------------ Balance Display ------------------ #
def print_balances(balances):
    print("\n📊 Balances:")

    empty = True
    for user, amount in balances.items():
        if abs(amount) < 1e-6:
            continue

        empty = False

        if amount > 0:
            print(f"{user} gets ₹{amount}")
        else:
            print(f"{user} owes ₹{abs(amount)}")

    if empty:
        print("All settled ✅")


# ------------------ Signup ------------------ #
def signup(sock):
    while True:
        print("\n--- SIGNUP ---")
        username = input("Choose username: ")
        if not username:
            print("❌ Username cannot be empty")
            continue

        password = input("Choose password: ")
        confirm = input("Confirm password: ")

        if password != confirm:
            print("❌ Passwords do not match")
            continue

        send(sock, {
            "action": "signup",
            "data": {"username": username, "password": password}
        })

        res = receive()

        if res and res.get("status") == "ok":
            print("✅ Signup successful")
            return username
        else:
            print(f"❌ {res.get('message', 'Signup failed')}")


# ------------------ Login ------------------ #
def login(sock):
    while True:
        print("\n--- LOGIN ---")
        username = input("Username: ")
        password = input("Password: ")

        send(sock, {
            "action": "login",
            "data": {"username": username, "password": password}
        })

        res = receive()

        if res and res.get("status") == "ok":
            print("✅ Login successful")
            return username
        else:
            print("❌ Invalid credentials")


# ------------------ Main Menu ------------------ #
def main_menu(sock, user):
    while True:
        print("\n--- MAIN MENU ---")
        print("1. View Groups")
        print("2. Create Group")
        print("3. Join Group")
        print("4. Open Group")
        print("0. Logout")

        choice = input("Enter choice: ")

        if choice == "1":
            send(sock, {"action": "list_groups"})
            print_response(receive())

        elif choice == "2":
            name = input("Enter group name (or 0 to cancel): ")
            if name == "0":
                continue

            password = input("Set group password (leave empty for no password): ")

            send(sock, {
                "action": "create_group",
                "data": {"group": name, "password": password}
            })
            print_response(receive())

        elif choice == "3":
            name = input("Enter group name (or 0 to cancel): ")
            if name == "0":
                continue

            password = input("Enter group password (or leave empty): ")

            send(sock, {
                "action": "join_group",
                "data": {"group": name, "password": password}
            })
            print_response(receive())

        elif choice == "4":
            send(sock, {"action": "list_groups"})
            res = receive()

            if not res or not res.get("groups"):
                print("No groups found. Create or join one first.")
                continue

            print("\n📂 Your Groups:")
            for i, g in enumerate(res["groups"]):
                print(f"{i+1}. {g}")

            sel = input("\nEnter number to open (or 0 to cancel): ")
            if sel == "0":
                continue

            try:
                idx = int(sel) - 1
                if idx < 0 or idx >= len(res["groups"]):
                    print("❌ Invalid selection")
                    continue
                group_menu(sock, user, res["groups"][idx])
            except:
                print("❌ Invalid input")

        elif choice == "0":
            print("👋 Logged out")
            break

        else:
            print("Invalid choice")


# ------------------ Group Menu ------------------ #
def group_menu(sock, user, group):
    while True:
        print(f"\n--- GROUP: {group} ---")
        print("1. Add Transaction")
        print("2. View Transactions")
        print("3. Delete Transaction")
        print("4. View Balances")
        print("5. Settle Transactions")
        print("0. Back")

        choice = input("Enter choice: ")

        # ---------------- ADD ---------------- #
        if choice == "1":
            amt = input("Amount (or 0 to cancel): ")
            if amt == "0":
                continue

            try:
                amount = float(amt)
            except:
                print("❌ Invalid amount")
                continue

            description = input("Description: ")

            send(sock, {
                "action": "get_group_members",
                "data": {"group": group}
            })

            res = receive()
            if res and res.get("status") == "ok" and res.get("members"):
                members = [m for m in res["members"] if m != user]
                print(f"\n👥 Group members (excluding you): {', '.join(members)}")
            else:
                members = []
                print("\n⚠️ Could not fetch members")

            users = input("Split between (comma-separated names, or 0 to cancel): ")
            if users == "0":
                continue

            users = [u.strip() for u in users.split(",") if u.strip()]

            if user in users:
                users.remove(user)

            if not users:
                print("❌ Must specify at least one person to split with")
                continue

            include_self = input("Include yourself in split? (y/n): ").strip().lower()
            include_self = include_self == "y"

            send(sock, {
                "action": "add_transaction",
                "data": {
                    "group": group,
                    "amount": amount,
                    "description": description,
                    "split_between": users,
                    "include_payer": include_self
                }
            })

            print_response(receive())

        # ---------------- VIEW TXN ---------------- #
        elif choice == "2":
            send(sock, {
                "action": "view_transactions",
                "data": {"group": group}
            })

            res = receive()

            print("\n📜 Transactions:")
            if res and res.get("transactions"):
                for i, txn in enumerate(res["transactions"]):
                    payer = txn["payer"]
                    amt = txn["amount"]
                    desc = txn.get("description", "")
                    people = txn["split_between"]
                    include_payer = txn.get("include_payer", False)
                    payer_note = " (you included)" if include_payer else ""
                    desc_note = f" - {desc}" if desc else ""
                    print(f"{i+1}: {payer} paid ₹{amt} for {', '.join(people)}{payer_note}{desc_note}")
            else:
                print("No transactions found")

        # ---------------- DELETE ---------------- #
        elif choice == "3":
            send(sock, {
                "action": "view_transactions",
                "data": {"group": group}
            })

            res = receive()

            if not res or not res.get("transactions"):
                print("No transactions to delete")
                continue

            print("\n📜 Select transaction to delete:")
            for i, txn in enumerate(res["transactions"]):
                payer = txn["payer"]
                amt = txn["amount"]
                desc = txn.get("description", "")
                people = txn["split_between"]
                include_payer = txn.get("include_payer", False)
                payer_note = " (you included)" if include_payer else ""
                desc_note = f" - {desc}" if desc else ""
                print(f"{i+1}: {payer} paid ₹{amt} for {', '.join(people)}{payer_note}{desc_note}")

            idx = input("\nEnter number (or 0 to cancel): ")
            if idx == "0":
                continue

            try:
                idx = int(idx) - 1
                if idx < 0 or idx >= len(res["transactions"]):
                    print("❌ Invalid selection")
                    continue
            except:
                print("❌ Invalid input")
                continue

            send(sock, {
                "action": "delete_transaction",
                "data": {"group": group, "index": idx}
            })
            print_response(receive())

        # ---------------- VIEW BALANCES ---------------- #
        elif choice == "4":
            send(sock, {
                "action": "view_balances",
                "data": {"group": group}
            })

            res = receive()

            if res and "balances" in res:
                print_balances(res["balances"])
            else:
                print("❌ Could not fetch balances")

        # ---------------- SETTLE ---------------- #
        elif choice == "5":
            send(sock, {
                "action": "settle",
                "data": {"group": group}
            })

            res = receive()

            print("\n💸 Settlement Result:")
            if res and res.get("settlements"):
                for s in res["settlements"]:
                    print(f"{s['from']} → {s['to']} : ₹{s['amount']}")
            else:
                print("Nothing to settle")

        elif choice == "0":
            break

        else:
            print("Invalid choice")


# ------------------ Start ------------------ #
def start_client():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))

    print("✅ Connected to server")

    thread = threading.Thread(target=listen_server, args=(sock,), daemon=True)
    thread.start()

    while True:
        print("\n--- WELCOME ---")
        print("1. Login")
        print("2. Signup")
        print("0. Exit")

        choice = input("Enter choice: ")

        if choice == "1":
            user = login(sock)
            main_menu(sock, user)
            break
        elif choice == "2":
            signup(sock)
            continue
        elif choice == "0":
            print("👋 Goodbye")
            sock.close()
            return
        else:
            print("Invalid choice")

    sock.close()
    print("Disconnected")


if __name__ == "__main__":
    start_client()
