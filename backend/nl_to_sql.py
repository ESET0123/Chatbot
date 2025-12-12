import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"

def nl_to_sql(query: str, db_content: str, conversation_history: list = None):
    """
    Convert natural language to SQL with conversation context
    
    Args:
        query: Current user query
        db_content: Database schema information
        conversation_history: List of previous {query, sql} pairs (last 7)
    """
    
    # Build context from conversation history
    context_section = ""
    if conversation_history and len(conversation_history) > 0:
        context_section = "\n\nPrevious conversation context:\n"
        for idx, item in enumerate(conversation_history[-7:], 1):  # Last 7 only
            context_section += f"{idx}. User asked: \"{item['query']}\"\n"
            context_section += f"   Generated SQL: {item['sql']}\n"
        context_section += "\nUse this context to understand references like 'that', 'those', 'same', etc.\n"
    
    prompt = f"""
    Database Schema:
    {db_content}

    {context_section}

    You are an SQL generator. Output ONLY valid SQL query, nothing else.
    - Use ONLY the tables and columns from the schema above
    - If the user refers to previous queries (like "show more", "same but...", "those results"), use the context
    - For follow-up questions, maintain continuity with previous queries
    
    Current question: {query}
    
    SQL Query:"""

    try:
        res = requests.post(OLLAMA_URL, json={
            "model": "gemma3:12b",
            "prompt": prompt,
            "stream": False  # Disable streaming for cleaner response
        })
        
        # Parse response
        sql_parts = []
        for line in res.text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                chunk = json.loads(line)
                resp = chunk.get("response", "")
                # Skip markdown code block markers
                if resp.strip() in ("```", "```sql", "sql"):
                    continue
                sql_parts.append(resp)
            except json.JSONDecodeError:
                continue

        sql = "".join(sql_parts).strip()
        
        # Clean up the SQL
        sql = sql.replace("```sql", "").replace("```", "").strip()
        
        print("Generated SQL with context:", sql)
        return sql

    except Exception as e:
        print("Error calling Ollama:", e)
        return ""


def build_context_prompt(conversation_history: list, max_context: int = 7):
    """
    Helper function to build a context-aware prompt from conversation history
    
    Args:
        conversation_history: Full conversation history
        max_context: Maximum number of previous exchanges to include
    
    Returns:
        Formatted context string
    """
    if not conversation_history or len(conversation_history) == 0:
        return ""
    
    # Take only the last N exchanges
    recent_history = conversation_history[-max_context:]
    
    context_lines = ["Previous conversation:"]
    for idx, exchange in enumerate(recent_history, 1):
        context_lines.append(f"\nQ{idx}: {exchange['query']}")
        if 'sql' in exchange:
            context_lines.append(f"SQL{idx}: {exchange['sql']}")
    
    return "\n".join(context_lines)