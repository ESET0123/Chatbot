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

class UserRegister(BaseModel):
    name: str
    email: str
    password: str
    role: Optional[str] = "user"  # Default role

class Token(BaseModel):
    access_token: str
    user_id: int
    email: str
    name: str
    role: str

class User(BaseModel):
    id: int
    name: str
    email: str
    role: str

# Database operations
def create_user(name: str, email: str, password: str, role: str = "user") -> Optional[int]:
    """Create a new user in the database"""
    conn = sqlite3.connect("./../mydata.db")
    cur = conn.cursor()
    
    try:
        # Check if email already exists
        cur.execute("SELECT id FROM users WHERE email = ?", (email,))
        existing_user = cur.fetchone()
        
        if existing_user:
            print(f"❌ Email {email} already exists")
            conn.close()
            return None
        
        # Insert new user
        cur.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            (name, email, password, role)
        )
        conn.commit()
        user_id = cur.lastrowid
        print(f"✅ User created: ID={user_id}, name={name}, email={email}, role={role}")
        conn.close()
        return user_id
        
    except sqlite3.IntegrityError as e:
        print(f"❌ Integrity error: {e}")
        conn.close()
        return None
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        conn.close()
        return None

def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email"""
    conn = sqlite3.connect("./../mydata.db")
    cur = conn.cursor()
    
    try:
        cur.execute(
            "SELECT id, name, email, password, role FROM users WHERE email = ?",
            (email,)
        )
        row = cur.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "password": row[3],
                "role": row[4] if row[4] else "user"
            }
        return None
    except Exception as e:
        print(f"❌ Error getting user by email: {e}")
        conn.close()
        return None

def get_user_by_id(user_id: int) -> Optional[dict]:
    """Get user by ID"""
    conn = sqlite3.connect("./../mydata.db")
    cur = conn.cursor()
    
    try:
        cur.execute(
            "SELECT id, name, email, role FROM users WHERE id = ?",
            (user_id,)
        )
        row = cur.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "role": row[3] if row[3] else "user"
            }
        return None
    except Exception as e:
        print(f"❌ Error getting user by ID: {e}")
        conn.close()
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
            "INSERT OR IGNORE INTO user_conversations (conversation_id, user_id) VALUES (?, ?)",
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
            conn.close()
            return True
        
        conn.close()
        if row[0] == user_id:
            return True
        
        return False
    except Exception as e:
        print(f"Error verifying conversation owner: {e}")
        conn.close()
        return False

def get_user_conversations(user_id: int) -> list:
    """Get all conversation IDs for a user"""
    conn = sqlite3.connect("./../mydata.db")
    cur = conn.cursor()
    
    try:
        cur.execute(
            "SELECT conversation_id FROM user_conversations WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        rows = cur.fetchall()
        conn.close()
        
        return [row[0] for row in rows]
    except Exception as e:
        print(f"Error getting user conversations: {e}")
        conn.close()
        return []