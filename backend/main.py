from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from db import run_sql, get_tables_with_columns
from nl_to_sql import nl_to_sql
from auth import (
    get_current_user, create_user, get_user_by_email,
    create_access_token, User, UserLogin, Token,
    link_conversation_to_user, verify_conversation_owner, 
    get_user_conversations
)

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
    user_id = create_user(user_data.email, user_data.password)
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    access_token = create_access_token(user_id)
    
    return Token(
        access_token=access_token,
        user_id=user_id,
        email=user_data.email
    )

@app.post("/auth/login", response_model=Token)
def login(user_data: UserLogin):
    """Login user"""
    user = get_user_by_email(user_data.email)
    # print("test3", user["name"])
    
    if not user or user["password"] != user_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(user["id"])
    
    return Token(
        access_token=access_token,
        user_id=user["id"],
        name=user["name"] or "guest",
        email=user["email"]
    )

@app.get("/auth/me", response_model=User)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return current_user

# Protected query endpoint
@app.post("/ask")
def ask(payload: Query, current_user: User = Depends(get_current_user)):
    nl_query = payload.query
    conversation_id = payload.conversation_id
    user_id = current_user.id
    
    if user_id not in user_conversation_contexts:
        user_conversation_contexts[user_id] = {}
    
    if conversation_id:
        if conversation_id not in user_conversation_contexts[user_id]:
            if not verify_conversation_owner(conversation_id, user_id):
                user_conversation_contexts[user_id][conversation_id] = []
                link_conversation_to_user(conversation_id, user_id)
        conversation_history = user_conversation_contexts[user_id][conversation_id]
    else:
        conversation_history = []
        if payload.conversation_history:
            conversation_history = [
                {"query": item.query, "sql": item.sql} 
                for item in payload.conversation_history
            ]
    
    db_content = get_tables_with_columns() 
    sql_query = nl_to_sql(nl_query, db_content, conversation_history[-7:])
    result = run_sql(sql_query)
    
    if conversation_id:
        user_conversation_contexts[user_id][conversation_id].append({
            "query": nl_query,
            "sql": sql_query
        })
        user_conversation_contexts[user_id][conversation_id] = \
            user_conversation_contexts[user_id][conversation_id][-7:]
    
    if should_generate_chart(nl_query, result):
        chart_config = generate_chart_config(result, nl_query)
        if chart_config:
            return {
                "sql": sql_query,
                "result": result,
                "chart": chart_config,
                "response_type": "chart"
            }
    
    return {
        "sql": sql_query,
        "result": result,
        "response_type": "table"
    }

@app.get("/conversations")
def list_conversations(current_user: User = Depends(get_current_user)):
    """List all conversations for the current user"""
    conversation_ids = get_user_conversations(current_user.id)
    return {"conversations": conversation_ids}

@app.get("/context/{conversation_id}")
def get_context(conversation_id: str, current_user: User = Depends(get_current_user)):
    """Get conversation context for a specific conversation"""
    user_id = current_user.id
    
    if not verify_conversation_owner(conversation_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this conversation"
        )
    
    context = user_conversation_contexts.get(user_id, {}).get(conversation_id, [])
    return {
        "conversation_id": conversation_id,
        "context": context
    }

@app.delete("/context/{conversation_id}")
def clear_context(conversation_id: str, current_user: User = Depends(get_current_user)):
    """Clear conversation context"""
    user_id = current_user.id
    
    if not verify_conversation_owner(conversation_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this conversation"
        )
    
    if user_id in user_conversation_contexts:
        if conversation_id in user_conversation_contexts[user_id]:
            del user_conversation_contexts[user_id][conversation_id]
    
    return {"message": "Context cleared"}