import sqlite3
from typing import Optional, List, Dict
from datetime import datetime

DB_PATH = "./../mydata.db"

def init_user_context(user_id: int):
    """Initialize context storage for a user - creates tables if needed"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # Ensure user_conversations table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_conversations (
                conversation_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Ensure conversation_history table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                conversation_id TEXT NOT NULL,
                query TEXT NOT NULL,
                sql TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Create index if not exists
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversation_history_user_conv 
            ON conversation_history(user_id, conversation_id)
        """)
        
        conn.commit()
    except Exception as e:
        print(f"Error initializing user context: {e}")
    finally:
        conn.close()

def get_conversation_history(user_id: int, conversation_id: str) -> list:
    """Get conversation history for a specific conversation from database"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT query, sql, created_at 
            FROM conversation_history 
            WHERE user_id = ? AND conversation_id = ?
            ORDER BY created_at ASC
        """, (user_id, conversation_id))
        
        rows = cur.fetchall()
        return [{"query": row[0], "sql": row[1], "created_at": row[2]} for row in rows]
    except Exception as e:
        print(f"Error fetching conversation history: {e}")
        return []
    finally:
        conn.close()

def save_conversation_exchange(user_id: int, conversation_id: str, query: str, sql: str):
    """Save a query-sql exchange to database"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # First, ensure the conversation exists in user_conversations
        cur.execute("""
            INSERT OR IGNORE INTO user_conversations (conversation_id, user_id, created_at)
            VALUES (?, ?, ?)
        """, (conversation_id, user_id, datetime.now().isoformat()))
        
        # Then save the exchange
        cur.execute("""
            INSERT INTO conversation_history (user_id, conversation_id, query, sql, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, conversation_id, query, sql, datetime.now().isoformat()))
        
        conn.commit()
        print(f"✅ Saved conversation exchange: {conversation_id}")
    except Exception as e:
        print(f"Error saving conversation exchange: {e}")
        conn.rollback()
    finally:
        conn.close()

def clear_conversation(user_id: int, conversation_id: str):
    """Clear conversation history"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            DELETE FROM conversation_history 
            WHERE user_id = ? AND conversation_id = ?
        """, (user_id, conversation_id))
        
        cur.execute("""
            DELETE FROM user_conversations 
            WHERE user_id = ? AND conversation_id = ?
        """, (user_id, conversation_id))
        
        conn.commit()
    except Exception as e:
        print(f"Error clearing conversation: {e}")
    finally:
        conn.close()

def get_user_all_conversations(user_id: int) -> List[Dict]:
    """Get all conversations for a user with metadata"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT 
                uc.conversation_id,
                uc.created_at,
                (SELECT query FROM conversation_history 
                 WHERE conversation_id = uc.conversation_id 
                 AND user_id = ?
                 ORDER BY created_at ASC LIMIT 1) as first_query,
                (SELECT MAX(created_at) FROM conversation_history 
                 WHERE conversation_id = uc.conversation_id
                 AND user_id = ?) as last_updated
            FROM user_conversations uc
            WHERE uc.user_id = ?
            ORDER BY COALESCE(last_updated, uc.created_at) DESC
        """, (user_id, user_id, user_id))
        
        rows = cur.fetchall()
        
        result = []
        for row in rows:
            conv_id = row[0]
            created_at = row[1]
            first_query = row[2]
            last_updated = row[3]
            
            title = first_query[:50] if first_query else "New Chat"
            
            result.append({
                "conversation_id": conv_id,
                "created_at": created_at,
                "title": title,
                "last_updated": last_updated or created_at
            })
        
        print(f"📋 Found {len(result)} conversations for user {user_id}")
        return result
        
    except Exception as e:
        print(f"Error fetching user conversations: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        conn.close()

def get_conversation_messages_with_results(user_id: int, conversation_id: str):
    """Get conversation messages with their SQL queries"""
    from db import run_sql
    
    history = get_conversation_history(user_id, conversation_id)
    messages = []
    
    for item in history:
        # Add user message
        messages.append({
            "type": "user",
            "content": item["query"],
            "sql": item["sql"],
            "created_at": item["created_at"]
        })
        
        # Execute SQL and add bot response
        try:
            result = run_sql(item["sql"])
            messages.append({
                "type": "bot",
                "result": result,
                "sql": item["sql"],
                "created_at": item["created_at"]
            })
        except Exception as e:
            messages.append({
                "type": "bot",
                "error": str(e),
                "created_at": item["created_at"]
            })
    
    return messages