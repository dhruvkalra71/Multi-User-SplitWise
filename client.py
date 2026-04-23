import socket
import threading
import json

HOST = "127.0.0.1"   # change if server is remote
PORT = 5000


# ------------------ Utility ------------------ #
def send(sock, msg):
    sock.sendall((json.dumps(msg) + "\n").encode())


def receive(sock):
    data = sock.recv(4096)
    if not data:
        return None
    return json.loads(data.decode())


# ------------------ Listener Thread ------------------ #
def listen_server(sock):
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                break

            messages = data.decode().strip().split("\n")
            for msg in messages:
                res = json.loads(msg)

                # Notifications / async messages
                if res.get("type") == "notification":
                    print(f"\n{res['message']}")
                elif res.get("type") == "settlement":
                    print("\nSettlement Suggestions:")
                    for s in res["data"]:
                        print(f"{s['from']} → {s['to']} : ₹{s['amount']}")
                else:
                    print(f"\n[SERVER]: {res}")

        except:
            break


# ------------------ CLI Logic ------------------ #

def login(sock):
    while True:
        username = input("Username: ")
        password = input("Password: ")

        send(sock, {
            "action": "login",
            "data": {"username": username, "password": password}
        })

        res = receive(sock)
        if res and res["status"] == "ok":
            print("Login successful")
            return username
        else:
            print("Invalid credentials")


def main_menu(sock):
    while True:
        print("\n--- MAIN MENU ---")
        print("1. View Groups")
        print("2. Create Group")
        print("3. Join Group")
        print("4. Logout")

        choice = input("Enter choice: ")

        if choice == "1":
            send(sock, {"action": "list_groups"})
            res = receive(sock)
            print("Your Groups:", res.get("groups", []))

        elif choice == "2":
            name = input("Group name: ")
            send(sock, {"action": "create_group", "data": {"group": name}})
            print(receive(sock))

        elif choice == "3":
            name = input("Enter group name: ")
            send(sock, {"action": "join_group", "data": {"group": name}})
            print(receive(sock))
            group_menu(sock, name)

        elif choice == "4":
            print("Logging out...")
            break


def group_menu(sock, group):
    while True:
        print(f"\n--- GROUP: {group} ---")
        print("1. Add Transaction")
        print("2. View Transactions")
        print("3. Delete Transaction")
        print("4. Settle Transactions")
        print("5. Exit Group")

        choice = input("Enter choice: ")

        if choice == "1":
            amount = float(input("Amount: "))
            users = input("Split between (comma separated): ").split(",")

            send(sock, {
                "action": "add_transaction",
                "data": {
                    "group": group,
                    "amount": amount,
                    "split_between": users
                }
            })
            print(receive(sock))

        elif choice == "2":
            send(sock, {
                "action": "view_transactions",
                "data": {"group": group}
            })
            res = receive(sock)

            print("\nTransactions:")
            for i, txn in enumerate(res.get("transactions", [])):
                print(f"{i}: {txn}")

        elif choice == "3":
            idx = int(input("Enter transaction index: "))
            send(sock, {
                "action": "delete_transaction",
                "data": {"group": group, "index": idx}
            })
            print(receive(sock))

        elif choice == "4":
            send(sock, {
                "action": "settle",
                "data": {"group": group}
            })
            print(receive(sock))

        elif choice == "5":
            break


# ------------------ Main ------------------ #

def start_client():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))

    # Start listener thread
    thread = threading.Thread(target=listen_server, args=(sock,), daemon=True)
    thread.start()

    print("Connected to server")

    user = login(sock)
    main_menu(sock)

    sock.close()


if __name__ == "__main__":
    start_client()
