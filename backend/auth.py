from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import sqlite3
from typing import Optional
import secrets

security = HTTPBearer()

# Simple in-memory token storage
active_tokens = {}  # {token: user_id}



# Models
class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    user_id: int
    email: str
    name: str

class User(BaseModel):
    id: int
    name: str
    email: str

# Database operations
def create_user(email: str, password: str) -> Optional[int]:
    """Create a new user in the database"""
    conn = sqlite3.connect("./../mydata.db")
    cur = conn.cursor()
    
    try:
        cur.execute(
            "INSERT INTO users (email, password) VALUES (?, ?)",
            (email, password)
        )
        conn.commit()
        user_id = cur.lastrowid
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None

def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email"""
    conn = sqlite3.connect("./../mydata.db")
    cur = conn.cursor()
    
    cur.execute(
        "SELECT id, name, email, password FROM users WHERE email = ?",
        (email,)
    )
    row = cur.fetchone()
    # print("test1", row)

    conn.close()
    
    if row:
        return {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "password": row[3]
        }
    return None

def get_user_by_id(user_id: int) -> Optional[dict]:
    """Get user by ID"""
    conn = sqlite3.connect("./../mydata.db")
    cur = conn.cursor()
    
    cur.execute(
        "SELECT id, name, email FROM users WHERE id = ?",
        (user_id,)
    )
    row = cur.fetchone()
    # print("test2", row)
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "name": row[1],
            "email": row[2]
        }
    return None

# Token operations
def create_access_token(user_id: int) -> str:
    """Create a simple access token"""
    token = secrets.token_urlsafe(32)
    active_tokens[token] = user_id
    return token

def get_user_from_token(token: str) -> Optional[int]:
    """Get user ID from token"""
    return active_tokens.get(token)

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user from token"""
    token = credentials.credentials
    user_id = get_user_from_token(token)
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return User(**user)

# User-specific conversation management
def link_conversation_to_user(conversation_id: str, user_id: int):
    """Link a conversation to a user"""
    conn = sqlite3.connect("./../mydata.db")
    cur = conn.cursor()
    
    try:
        cur.execute(
            "INSERT OR REPLACE INTO user_conversations (conversation_id, user_id) VALUES (?, ?)",
            (conversation_id, user_id)
        )
        conn.commit()
    except Exception as e:
        print(f"Error linking conversation: {e}")
    finally:
        conn.close()

def verify_conversation_owner(conversation_id: str, user_id: int) -> bool:
    """Verify that a conversation belongs to a user"""
    conn = sqlite3.connect("./../mydata.db")
    cur = conn.cursor()
    
    try:
        cur.execute(
            "SELECT user_id FROM user_conversations WHERE conversation_id = ?",
            (conversation_id,)
        )
        row = cur.fetchone()
        
        if row is None:
            # Conversation doesn't exist yet, allow creation
            return True
        
        if row[0] == user_id:
            return True
        
        return False
    except Exception as e:
        print(f"Error verifying conversation owner: {e}")
        return False
    finally:
        conn.close()

def link_conversation_to_user(conversation_id: str, user_id: int):
    """Link a conversation to a user"""
    conn = sqlite3.connect("./../mydata.db")
    cur = conn.cursor()
    
    try:
        cur.execute(
            "INSERT OR IGNORE INTO user_conversations (conversation_id, user_id) VALUES (?, ?)",
            (conversation_id, user_id)
        )
        conn.commit()
        print(f"✅ Linked conversation {conversation_id} to user {user_id}")
    except Exception as e:
        print(f"Error linking conversation: {e}")
    finally:
        conn.close()

def get_user_conversations(user_id: int) -> list:
    """Get all conversation IDs for a user"""
    conn = sqlite3.connect("./../mydata.db")
    cur = conn.cursor()
    
    cur.execute(
        "SELECT conversation_id FROM user_conversations WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    rows = cur.fetchall()
    conn.close()
    
    return [row[0] for row in rows]