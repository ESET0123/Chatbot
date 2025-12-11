from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import logging

from db import run_sql, get_tables_with_columns
from nl_to_sql import nl_to_sql
from auth import (
    get_current_user, create_user, get_user_by_email,
    create_access_token, User, UserLogin, Token,
    link_conversation_to_user, verify_conversation_owner, 
    get_user_conversations
)

# Logging config
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

# In-memory per-user context
user_conversation_contexts = {}

class ConversationExchange(BaseModel):
    query: str
    sql: str

class Query(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    conversation_history: Optional[List[ConversationExchange]] = None


# ----------- CHART DECISION LOGIC -----------
def should_generate_chart(query: str, result: dict) -> bool:
    if "error" in result or not result.get("rows"):
        return False

    chart_keywords = [
        'chart', 'graph', 'plot', 'visualize', 'visual',
        'trend', 'compare', 'comparison', 'distribution',
        'over time', 'by month', 'by year', 'by category'
    ]

    q = query.lower()
    for k in chart_keywords:
        if k in q:
            return True

    # auto-detect numeric 2-column output
    if len(result["columns"]) == 2 and len(result["rows"]) > 1:
        try:
            float(result["rows"][0][1])
            return True
        except:
            pass

    return False


def generate_chart_config(result: dict, query: str):
    columns = result["columns"]
    rows = result["rows"]

    if len(columns) < 2 or not rows:
        return None

    labels = [str(row[0]) for row in rows]

    q = query.lower()
    chart_type = "bar"
    if "line" in q or "trend" in q or "over time" in q:
        chart_type = "line"
    elif "pie" in q:
        chart_type = "pie"

    colors = [
        'rgba(102, 126, 234, 0.8)',
        'rgba(118, 75, 162, 0.8)',
        'rgba(240, 147, 251, 0.8)',
        'rgba(245, 87, 108, 0.8)',
        'rgba(67, 206, 162, 0.8)',
    ]

    datasets = []
    for i in range(1, len(columns)):
        data = []
        for row in rows:
            try:
                data.append(float(row[i]))
            except:
                data.append(0)

        datasets.append({
            'label': columns[i],
            'data': data,
            'backgroundColor': colors[i % len(colors)],
            'borderColor': colors[i % len(colors)].replace("0.8", "1"),
            'borderWidth': 2
        })

    return {
        "type": chart_type,
        "data": {
            "labels": labels,
            "datasets": datasets
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {
                    "display": len(datasets) > 1,
                    "position": "top"
                },
                "title": {"display": False}
            },
            "scales": {
                "y": {"beginAtZero": True}
            } if chart_type != "pie" else {}
        }
    }


# ----------- AUTH ENDPOINTS -----------
@app.post("/auth/register", response_model=Token)
def register(user_data: UserLogin):
    logger.info("=" * 60)
    logger.info("🔐 REGISTER ENDPOINT HIT")
    logger.info(f"Email: {user_data.email}")

    user_id = create_user(user_data.email, user_data.password)
    logger.info(f"User created with ID: {user_id}")

    if user_id is None:
        logger.error("❌ Email already exists")
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    access_token = create_access_token(user_id)
    logger.info(f"✅ Token created: {access_token[:20]}...")

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
    logger.info("=" * 60)
    logger.info("🔐 LOGIN ENDPOINT HIT")
    logger.info(f"Email: {user_data.email}")

    user = get_user_by_email(user_data.email)
    logger.info(f"User found: {user}")

    if not user or user["password"] != user_data.password:
        logger.error("❌ Invalid credentials")
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )

    access_token = create_access_token(user["id"])
    logger.info(f"✅ Token created: {access_token[:20]}...")

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
    logger.info("=" * 60)
    logger.info("👤 /auth/me ENDPOINT HIT")
    logger.info(f"Current user: {current_user}")
    logger.info("=" * 60)
    return current_user


# ----------- ASK ENDPOINT -----------
@app.post("/ask")
def ask(payload: Query, current_user: User = Depends(get_current_user)):
    logger.info("=" * 80)
    logger.info("🚀 /ASK ENDPOINT HIT")
    logger.info(f"User: {current_user.email} (ID: {current_user.id})")
    logger.info(f"Query: {payload.query}")
    logger.info(f"Conversation ID: {payload.conversation_id}")

    user_id = current_user.id
    nl_query = payload.query
    conversation_id = payload.conversation_id

    # Init user memory
    if user_id not in user_conversation_contexts:
        logger.info(f"Creating new context storage for user {user_id}")
        user_conversation_contexts[user_id] = {}

    # Manage conversation context
    if conversation_id:
        logger.info(f"Using conversation ID: {conversation_id}")

        if conversation_id not in user_conversation_contexts[user_id]:
            if not verify_conversation_owner(conversation_id, user_id):
                logger.info("Creating new conversation context")
                user_conversation_contexts[user_id][conversation_id] = []
                link_conversation_to_user(conversation_id, user_id)

        conversation_history = user_conversation_contexts[user_id][conversation_id]
        logger.info(f"Conversation history length: {len(conversation_history)}")

    else:
        conversation_history = []
        if payload.conversation_history:
            conversation_history = [
                {"query": item.query, "sql": item.sql}
                for item in payload.conversation_history
            ]
            logger.info(f"Using provided history: {len(conversation_history)}")

    # DB schema
    logger.info("📊 Getting database schema...")
    db_content = get_tables_with_columns()
    logger.info(f"Schema retrieved: {db_content}")

    # SQL generation
    logger.info("🤖 Generating SQL...")
    sql_query = nl_to_sql(nl_query, db_content, conversation_history[-7:])
    logger.info(f"Generated SQL: {sql_query}")

    # Execute SQL
    logger.info("💾 Executing SQL query...")
    result = run_sql(sql_query)
    logger.info(f"Query result: {len(result.get('rows', []))} rows")

    # Save context
    if conversation_id:
        logger.info("Saving to conversation context...")
        user_conversation_contexts[user_id][conversation_id].append({
            "query": nl_query,
            "sql": sql_query
        })
        user_conversation_contexts[user_id][conversation_id] = \
            user_conversation_contexts[user_id][conversation_id][-7:]
        logger.info(f"Context updated: {len(user_conversation_contexts[user_id][conversation_id])} items")

    # Chart check
    if should_generate_chart(nl_query, result):
        logger.info("📈 Generating chart...")
        chart_config = generate_chart_config(result, nl_query)
        logger.info("Returning chart response")
        logger.info("=" * 80)
        return {
            "sql": sql_query,
            "result": result,
            "chart": chart_config,
            "response_type": "chart"
        }

    logger.info("Returning table response")
    logger.info("=" * 80)
    return {
        "sql": sql_query,
        "result": result,
        "response_type": "table"
    }


# ----------- CONVERSATION APIs -----------
@app.get("/conversations")
def list_conversations(current_user: User = Depends(get_current_user)):
    logger.info("📋 /conversations HIT")
    conv_ids = get_user_conversations(current_user.id)
    logger.info(f"Found {len(conv_ids)} conversations")
    return {"conversations": conv_ids}


@app.get("/context/{conversation_id}")
def get_context(conversation_id: str, current_user: User = Depends(get_current_user)):
    logger.info(f"📖 /context/{conversation_id} HIT")

    user_id = current_user.id
    if not verify_conversation_owner(conversation_id, user_id):
        raise HTTPException(403, "Access denied")

    ctx = user_conversation_contexts.get(user_id, {}).get(conversation_id, [])
    logger.info(f"Context size: {len(ctx)}")
    return {"conversation_id": conversation_id, "context": ctx}


@app.delete("/context/{conversation_id}")
def clear_context(conversation_id: str, current_user: User = Depends(get_current_user)):
    logger.info(f"🗑️ Clearing context for {conversation_id}")

    user_id = current_user.id
    if not verify_conversation_owner(conversation_id, user_id):
        raise HTTPException(403, "Access denied")

    if user_id in user_conversation_contexts:
        user_conversation_contexts[user_id].pop(conversation_id, None)

    return {"message": "Context cleared"}
