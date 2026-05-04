# Multi-User SplitWise

A real-time, multi-user expense splitting system with optimized cash flow settlement, built using Python socket programming.

## Overview

SplitWise is a client-server application that allows multiple users to manage shared expenses in groups. It features real-time balance tracking, transaction management, and an optimized settlement algorithm that minimizes the total number of transactions needed to settle debts.

## Architecture

### Server (`server.py`)
- Multi-threaded TCP server using Python sockets
- Handles concurrent client connections
- Manages user authentication with local signup/login (`users.json`)
- Stores group data and transactions in `data.json`
- Supports the following operations:
  - User signup and login/logout
  - Create and join password-protected groups
  - Add, view, and delete transactions
  - View real-time balances
  - Generate optimized settlement plans

### Client (`client.py`)
- CLI-based interface for interacting with the server
- Real-time notification system for group updates
- Interactive menus for group and transaction management
- Threaded server listener for asynchronous notifications

### Settlement Algorithm (`settlement.py`)
- Implements minimum cash flow algorithm
- Reduces the number of transactions needed to settle all debts
- Uses a greedy approach to match maximum debtors with maximum creditors

## Features

- **User Authentication**: Sign up and login with credentials stored locally
- **Multi-user Support**: Multiple users can connect simultaneously
- **Group Management**: Create and join groups with optional password protection
- **Flexible Splitting**: Split expenses with or without including the payer
- **Real-time Updates**: Notifications broadcasted to all group members
- **Optimized Settlements**: Minimizes total transactions to settle debts
- **Persistent Storage**: Data saved to JSON file for persistence across restarts

## Installation

No external dependencies required. Uses Python standard library only.

```bash
# Clone the repository
git clone https://github.com/dhruvkalra71/Multi-User-SplitWise.git
cd Multi-User-SplitWise
```

## Usage

### Start the Server

```bash
python server.py
```

The server will start on `0.0.0.0:5005`.

### Start the Client

```bash
python client.py
```

The client will connect to `127.0.0.1:5005` and prompt you to signup or login.

## Data Structure

User credentials are stored in `users.json`:

```json
{
  "username1": "password1",
  "username2": "password2"
}
```

Group data is stored in `data.json`:

```json
{
  "groups": {
    "group_name": {
      "members": ["user1", "user2"],
      "transactions": [
        {
          "payer": "user1",
          "amount": 100.0,
          "description": "Dinner",
          "split_between": ["user2"],
          "include_payer": true
        }
      ],
      "password": "optional_password"
    }
  }
}
```

## Protocol

Client-server communication uses JSON messages over TCP with newline delimiters:

**Request Format:**
```json
{
  "action": "action_name",
  "data": { ... }
}
```

**Supported Actions:**
- `signup` - Create a new user account
- `login` - Authenticate user
- `create_group` - Create a new group
- `join_group` - Join an existing group
- `list_groups` - List user's groups
- `get_group_members` - Get members of a group
- `add_transaction` - Add a new transaction
- `view_transactions` - View group transactions
- `delete_transaction` - Delete a transaction
- `view_balances` - View group balances
- `settle` - Generate optimized settlement plan

## Project Structure

```
Multi-User-SplitWise/
├── server.py          # Multi-threaded TCP server
├── client.py          # CLI client application
├── settlement.py      # Minimum cash flow algorithm
├── data.json          # Group and transaction storage (local)
├── users.json         # User credentials storage (local)
└── webapp/            # Web application (excluded from repo)
```

## License

This project is open source and available under the MIT License.
