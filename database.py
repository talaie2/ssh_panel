import sqlite3
from datetime import datetime, timedelta

def init_db():
    conn = sqlite3.connect('ssh_panel.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        expiry_date TEXT,
        max_connections INTEGER,
        status TEXT DEFAULT 'active',
        host TEXT,
        port INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        server_index INTEGER,
        photo_id TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def add_user(username, password, expiry_days, max_connections, host, port):
    conn = sqlite3.connect('ssh_panel.db')
    c = conn.cursor()
    expiry_date = (datetime.now() + timedelta(days=expiry_days)).strftime('%Y-%m-%d')
    c.execute("INSERT INTO users (username, password, expiry_date, max_connections, host, port) VALUES (?, ?, ?, ?, ?, ?)",
              (username, password, expiry_date, max_connections, host, port))
    conn.commit()
    conn.close()

def get_user_info(user_id):
    conn = sqlite3.connect('ssh_panel.db')
    c = conn.cursor()
    c.execute("SELECT username, password, expiry_date, host, port FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return {"username": user[0], "password": user[1], "expiry_date": user[2], "host": user[3], "port": user[4]} if user else None

def add_request(user_id, server_index, photo_id):
    conn = sqlite3.connect('ssh_panel.db')
    c = conn.cursor()
    c.execute("INSERT INTO requests (user_id, server_index, photo_id) VALUES (?, ?, ?)", (user_id, server_index, photo_id))
    conn.commit()
    conn.close()

def get_pending_requests():
    conn = sqlite3.connect('ssh_panel.db')
    c = conn.cursor()
    c.execute("SELECT id, user_id, created_at, photo_id FROM requests WHERE status = 'pending'")
    requests = c.fetchall()
    conn.close()
    return requests

def update_request_status(request_id, status):
    conn = sqlite3.connect('ssh_panel.db')
    c = conn.cursor()
    c.execute("UPDATE requests SET status = ? WHERE id = ?", (status, request_id))
    conn.commit()
    conn.close()

def get_users():
    conn = sqlite3.connect('ssh_panel.db')
    c = conn.cursor()
    c.execute("SELECT username, password, expiry_date, host, port FROM users")
    users = c.fetchall()
    conn.close()
    return users

def update_server_list(servers):
    with open('servers.json', 'w') as f:
        json.dump(servers, f)