from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import logging

from conversation_manager import (
    init_user_context,
    get_conversation_history,
    save_conversation_exchange,
    clear_conversation,
    get_user_all_conversations,
    get_conversation_messages_with_results
)

from db import run_sql, get_tables_with_columns
from nl_to_sql import nl_to_sql
from chart_generator import should_generate_chart, generate_chart_config

from auth import (
    get_current_user, create_user, get_user_by_email,
    create_access_token, User, UserLogin, UserRegister, Token,
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


# Request Models
class ConversationExchange(BaseModel):
    query: str
    sql: str

class Query(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    conversation_history: Optional[List[ConversationExchange]] = None


# ----------- AUTH ENDPOINTS -----------
@app.post("/auth/register", response_model=Token)
def register(user_data: UserRegister):
    logger.info("=" * 60)
    logger.info("🔐 REGISTER ENDPOINT HIT")
    logger.info(f"Name: {user_data.name}")
    logger.info(f"Email: {user_data.email}")
    logger.info(f"Role: {user_data.role}")

    user_id = create_user(user_data.name, user_data.email, user_data.password, user_data.role)
    logger.info(f"User creation result: {user_id}")

    if user_id is None:
        logger.error("❌ Email already exists or creation failed")
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    access_token = create_access_token(user_id)
    logger.info(f"✅ Token created: {access_token[:20]}...")

    response = Token(
        access_token=access_token,
        user_id=user_id,
        email=user_data.email,
        name=user_data.name,
        role=user_data.role
    )
    logger.info(f"📤 Sending response")
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
        name=user["name"] or "User",
        email=user["email"],
        role=user.get("role", "user")
    )

    logger.info(f"📤 Sending response")
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

    # Initialize user context
    init_user_context(user_id)

    # Get conversation history
    if conversation_id:
        logger.info(f"Using conversation ID: {conversation_id}")

        # Verify or create conversation ownership
        if not verify_conversation_owner(conversation_id, user_id):
            logger.info("Creating new conversation context")
            link_conversation_to_user(conversation_id, user_id)

        conversation_history = get_conversation_history(user_id, conversation_id)
        logger.info(f"Conversation history length: {len(conversation_history)}")
    else:
        # Use provided history if no conversation_id
        conversation_history = []
        if payload.conversation_history:
            conversation_history = [
                {"query": item.query, "sql": item.sql}
                for item in payload.conversation_history
            ]
            logger.info(f"Using provided history: {len(conversation_history)}")

    # Get database schema
    logger.info("📊 Getting database schema...")
    db_content = get_tables_with_columns()
    logger.info(f"Schema retrieved: {db_content}")

    # Generate SQL
    logger.info("🤖 Generating SQL...")
    sql_query = nl_to_sql(nl_query, db_content, conversation_history[-7:])
    logger.info(f"Generated SQL: {sql_query}")

    # Execute SQL
    logger.info("💾 Executing SQL query...")
    result = run_sql(sql_query)
    logger.info(f"Query result: {len(result.get('rows', []))} rows")

    # Save to conversation context
    if conversation_id:
        logger.info("Saving to conversation context...")
        save_conversation_exchange(user_id, conversation_id, nl_query, sql_query)
        logger.info("Context updated")

    # Check if should generate chart
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
    """Get all conversations for the current user"""
    logger.info("=" * 60)
    logger.info(f"📋 /conversations HIT for user {current_user.id}")
    
    # Initialize tables if needed
    init_user_context(current_user.id)
    
    conversations = get_user_all_conversations(current_user.id)
    logger.info(f"Found {len(conversations)} conversations")
    
    for conv in conversations:
        logger.info(f"  - {conv['conversation_id']}: {conv['title']}")
    
    logger.info("=" * 60)
    return {"conversations": conversations}


@app.get("/context/{conversation_id}")
def get_context(conversation_id: str, current_user: User = Depends(get_current_user)):
    logger.info(f"📖 /context/{conversation_id} HIT")

    user_id = current_user.id
    if not verify_conversation_owner(conversation_id, user_id):
        raise HTTPException(403, "Access denied")

    ctx = get_conversation_history(user_id, conversation_id)
    logger.info(f"Context size: {len(ctx)}")
    return {"conversation_id": conversation_id, "context": ctx}


@app.delete("/context/{conversation_id}")
def clear_context(conversation_id: str, current_user: User = Depends(get_current_user)):
    logger.info(f"🗑️ Clearing context for {conversation_id}")

    user_id = current_user.id
    if not verify_conversation_owner(conversation_id, user_id):
        raise HTTPException(403, "Access denied")

    clear_conversation(user_id, conversation_id)
    return {"message": "Context cleared"}

@app.get("/conversations")
def list_conversations(current_user: User = Depends(get_current_user)):
    """Get all conversations for the current user"""
    logger.info(f"📋 /conversations HIT for user {current_user.id}")
    
    conversations = get_user_all_conversations(current_user.id)
    logger.info(f"Found {len(conversations)} conversations")
    
    return {"conversations": conversations}

@app.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(
    conversation_id: str, 
    current_user: User = Depends(get_current_user)
    ):
        """Get all messages in a conversation with their results"""
        logger.info("=" * 60)
        logger.info(f"📖 /conversations/{conversation_id}/messages HIT")
        logger.info(f"User: {current_user.id}")
        
        if not verify_conversation_owner(conversation_id, current_user.id):
            logger.error("❌ Access denied")
            raise HTTPException(403, "Access denied")
        
        messages = get_conversation_messages_with_results(current_user.id, conversation_id)
        logger.info(f"Retrieved {len(messages)} messages")
        logger.info("=" * 60)
        
        return {
            "conversation_id": conversation_id,
            "messages": messages
        }

@app.get("/debug/routes")
def list_routes():
    """List all registered routes (for debugging)"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": route.name
            })
    return {"routes": routes}

@app.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str, 
    current_user: User = Depends(get_current_user)
):
    """Delete a conversation and all its messages"""
    logger.info("=" * 60)
    logger.info(f"🗑️ DELETE /conversations/{conversation_id}")
    logger.info(f"User: {current_user.id}")
    
    if not verify_conversation_owner(conversation_id, current_user.id):
        logger.error("❌ Access denied")
        raise HTTPException(403, "Access denied")
    
    try:
        clear_conversation(current_user.id, conversation_id)
        logger.info("✅ Conversation deleted successfully")
        logger.info("=" * 60)
        return {"message": "Conversation deleted successfully"}
    except Exception as e:
        logger.error(f"❌ Error deleting conversation: {e}")
        raise HTTPException(500, "Failed to delete conversation")