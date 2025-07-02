import sqlite3

conn = sqlite3.connect("members.db")
c = conn.cursor()

# Add missing 'residence' column if it doesn't exist
try:
    c.execute("ALTER TABLE members ADD COLUMN residence TEXT")
    print("✅ Column 'residence' added.")
except sqlite3.OperationalError as e:
    print("⚠️ Column already exists or another error:", e)

conn.commit()
conn.close()
