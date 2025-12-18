import sqlite3

conn = sqlite3.connect("scraped_posts.db")
cur = conn.cursor()

# Add city column if it doesn't exist
try:
    cur.execute("ALTER TABLE posts ADD COLUMN city TEXT")
except sqlite3.OperationalError:
    pass  # column already exists

# Add group_name column if it doesn't exist
try:
    cur.execute("ALTER TABLE posts ADD COLUMN group_name TEXT")
except sqlite3.OperationalError:
    pass  # column already exists

conn.commit()
conn.close()
print("✅ Table updated with city and group_name columns")
