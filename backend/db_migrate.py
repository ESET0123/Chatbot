# migrate_tokens.py
import sqlite3

DB_PATH = "mydata.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("[migrate] ensuring tokens table...")
cur.execute("""
CREATE TABLE IF NOT EXISTS tokens (
  token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
)
""")

print("[migrate] ensuring user_conversations table...")
cur.execute("""
CREATE TABLE IF NOT EXISTS user_conversations (
  conversation_id TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
)
""")

print("[migrate] ensuring conversation_context table...")
cur.execute("""
CREATE TABLE IF NOT EXISTS conversation_context (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id TEXT NOT NULL,
  user_id INTEGER NOT NULL,
  user_query TEXT NOT NULL,
  sql_query TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
)
""")

print("[migrate] ensuring indices...")
cur.execute("CREATE INDEX IF NOT EXISTS idx_conv_context ON conversation_context(conversation_id, user_id, created_at)")

# Ensure users has necessary columns
print("[migrate] ensuring users columns(name, role)...")
cur.execute("PRAGMA table_info(users)")
cols = [row[1] for row in cur.fetchall()]
if 'name' not in cols:
    cur.execute("ALTER TABLE users ADD COLUMN name TEXT DEFAULT 'Guest'")
if 'role' not in cols:
    cur.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")

conn.commit()
conn.close()
print("[migrate] done.")
