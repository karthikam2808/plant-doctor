import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()
cursor.execute("ALTER TABLE history ADD COLUMN loss REAL;")
conn.commit()
conn.close()
print("✅ 'loss' column added to history table.")
