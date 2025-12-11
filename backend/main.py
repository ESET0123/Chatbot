from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import time
import logging

from db import run_sql, get_tables_with_columns
from nl_to_sql import nl_to_sql
from auth import (
    get_current_user, create_user, get_user_by_email,
    create_access_token, User, UserLogin, Token,
    link_conversation_to_user, verify_conversation_owner, 
    get_user_conversations
)

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Per-user conversation storage
user_conversation_contexts = {}

class ConversationExchange(BaseModel):
    query: str
    sql: str

class Query(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    conversation_history: Optional[List[ConversationExchange]] = None

def should_generate_chart(query: str, result: dict) -> bool:
    """Determine if the query should generate a chart"""
    if "error" in result or not result.get("rows"):
        return False
    
    chart_keywords = [
        'chart', 'graph', 'plot', 'visualize', 'visual', 
        'trend', 'compare', 'comparison', 'distribution',
        'over time', 'by month', 'by year', 'by category'
    ]
    
    query_lower = query.lower()
    for keyword in chart_keywords:
        if keyword in query_lower:
            return True
    
    if len(result["columns"]) == 2 and len(result["rows"]) > 1:
        try:
            float(result["rows"][0][1])
            return True
        except (ValueError, TypeError, IndexError):
            pass
    
    return False

def generate_chart_config(result: dict, query: str):
    """Generate Chart.js configuration based on result data"""
    columns = result["columns"]
    rows = result["rows"]
    
    if len(columns) < 2 or len(rows) == 0:
        return None
    
    labels = [str(row[0]) for row in rows]
    
    query_lower = query.lower()
    chart_type = 'bar'
    
    if 'line' in query_lower or 'trend' in query_lower or 'over time' in query_lower:
        chart_type = 'line'
    elif 'pie' in query_lower:
        chart_type = 'pie'
    
    datasets = []
    colors = [
        'rgba(102, 126, 234, 0.8)',
        'rgba(118, 75, 162, 0.8)',
        'rgba(240, 147, 251, 0.8)',
        'rgba(245, 87, 108, 0.8)',
        'rgba(67, 206, 162, 0.8)',
    ]
    
    for i in range(1, len(columns)):
        data = []
        for row in rows:
            try:
                data.append(float(row[i]))
            except (ValueError, TypeError):
                data.append(0)
        
        datasets.append({
            'label': columns[i],
            'data': data,
            'backgroundColor': colors[i % len(colors)],
            'borderColor': colors[i % len(colors)].replace('0.8', '1'),
            'borderWidth': 2
        })
    
    config = {
        'type': chart_type,
        'data': {
            'labels': labels,
            'datasets': datasets
        },
        'options': {
            'responsive': True,
            'maintainAspectRatio': False,
            'plugins': {
                'legend': {
                    'display': len(datasets) > 1,
                    'position': 'top'
                },
                'title': {
                    'display': False
                }
            },
            'scales': {
                'y': {
                    'beginAtZero': True
                }
            } if chart_type != 'pie' else {}
        }
    }
    
    return config

# Authentication endpoints
@app.post("/auth/register", response_model=Token)
def register(user_data: UserLogin):
    """Register a new user"""
    logger.info("=" * 60)
    logger.info("🔐 REGISTER ENDPOINT HIT")
    logger.info(f"Email: {user_data.email}")
    time.sleep(1)
    
    user_id = create_user(user_data.email, user_data.password)
    logger.info(f"User created with ID: {user_id}")
    time.sleep(1)
    
    if user_id is None:
        logger.error("❌ Email already exists")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    access_token = create_access_token(user_id)
    logger.info(f"✅ Token created: {access_token[:20]}...")
    time.sleep(1)
    
    response = Token(
        access_token=access_token,
        user_id=user_id,
        email=user_data.email
    )
    logger.info(f"📤 Sending response: {response}")
    logger.info("=" * 60)
    return response

@app.post("/auth/login", response_model=Token)
def login(user_data: UserLogin):
    """Login user"""
    logger.info("=" * 60)
    logger.info("🔐 LOGIN ENDPOINT HIT")
    logger.info(f"Email: {user_data.email}")
    time.sleep(1)
    
    user = get_user_by_email(user_data.email)
    logger.info(f"User found: {user}")
    time.sleep(1)
    
    if not user or user["password"] != user_data.password:
        logger.error("❌ Invalid credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(user["id"])
    logger.info(f"✅ Token created: {access_token[:20]}...")
    time.sleep(1)
    
    response = Token(
        access_token=access_token,
        user_id=user["id"],
        name=user["name"] or "guest",
        email=user["email"]
    )
    logger.info(f"📤 Sending response: {response}")
    logger.info("=" * 60)
    return response

@app.get("/auth/me", response_model=User)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    logger.info("=" * 60)
    logger.info("👤 /auth/me ENDPOINT HIT")
    logger.info(f"Current user: {current_user}")
    logger.info("=" * 60)
    return current_user

# Protected query endpoint
@app.post("/ask")
def ask(payload: Query, current_user: User = Depends(get_current_user)):
    logger.info("=" * 80)
    logger.info("🚀 /ASK ENDPOINT HIT")
    logger.info(f"User: {current_user.email} (ID: {current_user.id})")
    logger.info(f"Query: {payload.query}")
    logger.info(f"Conversation ID: {payload.conversation_id}")
    time.sleep(2)
    
    nl_query = payload.query
    conversation_id = payload.conversation_id
    user_id = current_user.id
    
    if user_id not in user_conversation_contexts:
        logger.info(f"Creating new context storage for user {user_id}")
        user_conversation_contexts[user_id] = {}
        time.sleep(1)
    
    if conversation_id:
        logger.info(f"Using conversation ID: {conversation_id}")
        if conversation_id not in user_conversation_contexts[user_id]:
            logger.info("Conversation not in memory, verifying ownership...")
            if not verify_conversation_owner(conversation_id, user_id):
                logger.info("Creating new conversation context")
                user_conversation_contexts[user_id][conversation_id] = []
                link_conversation_to_user(conversation_id, user_id)
        conversation_history = user_conversation_contexts[user_id][conversation_id]
        logger.info(f"Conversation history length: {len(conversation_history)}")
        time.sleep(1)
    else:
        logger.info("No conversation ID provided")
        conversation_history = []
        if payload.conversation_history:
            conversation_history = [
                {"query": item.query, "sql": item.sql} 
                for item in payload.conversation_history
            ]
            logger.info(f"Using provided history: {len(conversation_history)} items")
        time.sleep(1)
    
    logger.info("📊 Getting database schema...")
    db_content = get_tables_with_columns()
    logger.info(f"Schema retrieved: {db_content}")
    time.sleep(1)
    
    logger.info("🤖 Generating SQL from natural language...")
    sql_query = nl_to_sql(nl_query, db_content, conversation_history[-7:])
    logger.info(f"Generated SQL: {sql_query}")
    time.sleep(2)
    
    logger.info("💾 Executing SQL query...")
    result = run_sql(sql_query)
    logger.info(f"Query result: {len(result.get('rows', []))} rows")
    time.sleep(1)
    
    if conversation_id:
        logger.info("Saving to conversation context...")
        user_conversation_contexts[user_id][conversation_id].append({
            "query": nl_query,
            "sql": sql_query
        })
        user_conversation_contexts[user_id][conversation_id] = \
            user_conversation_contexts[user_id][conversation_id][-7:]
        logger.info(f"Context updated, now has {len(user_conversation_contexts[user_id][conversation_id])} items")
        time.sleep(1)
    
    if should_generate_chart(nl_query, result):
        logger.info("📈 Generating chart...")
        chart_config = generate_chart_config(result, nl_query)
        if chart_config:
            logger.info("✅ Chart config created, returning chart response")
            time.sleep(1)
            logger.info("=" * 80)
            return {
                "sql": sql_query,
                "result": result,
                "chart": chart_config,
                "response_type": "chart"
            }
    
    logger.info("✅ Returning table response")
    time.sleep(1)
    logger.info("=" * 80)
    return {
        "sql": sql_query,
        "result": result,
        "response_type": "table"
    }

@app.get("/conversations")
def list_conversations(current_user: User = Depends(get_current_user)):
    """List all conversations for the current user"""
    logger.info("📋 /conversations endpoint hit")
    conversation_ids = get_user_conversations(current_user.id)
    logger.info(f"Found {len(conversation_ids)} conversations")
    return {"conversations": conversation_ids}

@app.get("/context/{conversation_id}")
def get_context(conversation_id: str, current_user: User = Depends(get_current_user)):
    """Get conversation context for a specific conversation"""
    logger.info(f"📖 /context/{conversation_id} endpoint hit")
    user_id = current_user.id
    
    if not verify_conversation_owner(conversation_id, user_id):
        logger.error("❌ Access denied")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this conversation"
        )
    
    context = user_conversation_contexts.get(user_id, {}).get(conversation_id, [])
    logger.info(f"Context retrieved: {len(context)} items")
    return {
        "conversation_id": conversation_id,
        "context": context
    }

@app.delete("/context/{conversation_id}")
def clear_context(conversation_id: str, current_user: User = Depends(get_current_user)):
    """Clear conversation context"""
    logger.info(f"🗑️ /context/{conversation_id} DELETE endpoint hit")
    user_id = current_user.id
    
    if not verify_conversation_owner(conversation_id, user_id):
        logger.error("❌ Access denied")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this conversation"
        )
    
    if user_id in user_conversation_contexts:
        if conversation_id in user_conversation_contexts[user_id]:
            del user_conversation_contexts[user_id][conversation_id]
            logger.info("✅ Context cleared")
    
    return {"message": "Context cleared"}