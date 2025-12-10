from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import re

from db import run_sql, get_tables_with_columns
from nl_to_sql import nl_to_sql

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for conversation contexts (per session/conversation)
conversation_contexts = {}

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
    
    # Keywords that suggest visualization
    chart_keywords = [
        'chart', 'graph', 'plot', 'visualize', 'visual', 
        'trend', 'compare', 'comparison', 'distribution',
        'over time', 'by month', 'by year', 'by category'
    ]
    
    query_lower = query.lower()
    for keyword in chart_keywords:
        if keyword in query_lower:
            return True
    
    # Auto-chart for numeric aggregations with categories
    if len(result["columns"]) == 2 and len(result["rows"]) > 1:
        # Check if second column contains numbers
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
    
    # Extract labels and data
    labels = [str(row[0]) for row in rows]
    
    # Determine chart type from query
    query_lower = query.lower()
    chart_type = 'bar'
    
    if 'line' in query_lower or 'trend' in query_lower or 'over time' in query_lower:
        chart_type = 'line'
    elif 'pie' in query_lower:
        chart_type = 'pie'
    
    # Handle multiple data series
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

@app.post("/ask")
def ask(payload: Query):
    nl_query = payload.query
    conversation_id = payload.conversation_id
    
    # Get or initialize conversation context
    if conversation_id:
        if conversation_id not in conversation_contexts:
            conversation_contexts[conversation_id] = []
        conversation_history = conversation_contexts[conversation_id]
    else:
        # Use history from frontend if provided
        conversation_history = []
        if payload.conversation_history:
            conversation_history = [
                {"query": item.query, "sql": item.sql} 
                for item in payload.conversation_history
            ]
    
    # Get database schema
    db_content = get_tables_with_columns() 
    print("DB Content:", db_content)
    
    # Generate SQL with conversation context (last 7 exchanges)
    sql_query = nl_to_sql(nl_query, db_content, conversation_history[-7:])
    # print("Generated SQL query:", sql_query)
    
    # Execute SQL
    result = run_sql(sql_query)
    # print("Result:", result)
    
    # Store this exchange in context
    if conversation_id:
        conversation_contexts[conversation_id].append({
            "query": nl_query,
            "sql": sql_query
        })
        # Keep only last 7 exchanges
        conversation_contexts[conversation_id] = conversation_contexts[conversation_id][-7:]
    
    # Check if we should generate a chart
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

@app.get("/context/{conversation_id}")
def get_context(conversation_id: str):
    """Get conversation context for a specific conversation"""
    return {
        "conversation_id": conversation_id,
        "context": conversation_contexts.get(conversation_id, [])
    }

@app.delete("/context/{conversation_id}")
def clear_context(conversation_id: str):
    """Clear conversation context"""
    if conversation_id in conversation_contexts:
        del conversation_contexts[conversation_id]
    return {"message": "Context cleared"}