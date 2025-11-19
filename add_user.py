import sqlite3

DB_PATH = "users.db"

# Change these values as needed
username = "admin","karthik"
password = "admin","1234"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
try:
    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    conn.commit()
    print(f"User '{username}' added successfully.")
except sqlite3.IntegrityError:
    print(f"User '{username}' already exists.")
finally:
    conn.close()
