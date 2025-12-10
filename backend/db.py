import sqlite3

DB_PATH = "mydata.db"

# Function to run any SQL query
def run_sql(sql: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] if cur.description else []
        conn.close()
        return {"columns": columns, "rows": rows}
    except Exception as e:
        conn.close()
        return {"error": str(e)}

# Function to get list of all user tables (excluding system tables)
def get_user_tables():
    sql = """
    SELECT name 
    FROM sqlite_master 
    WHERE type='table' 
      AND name NOT LIKE 'sqlite_%'
    ORDER BY name;
    """
    result = run_sql(sql)
    
    if "error" in result:
        return result
    
    # Additional filtering in Python for safety
    system_tables = ['sqlite_sequence', 'sqlite_stat1', 'sqlite_stat2', 'sqlite_stat3', 'sqlite_stat4']
    user_tables = [
        row[0] for row in result["rows"] 
        if row[0] not in system_tables
    ]
    
    return user_tables

# Function to get schema of a specific table
def get_table_schema(table_name: str):
    sql = f"PRAGMA table_info({table_name})"
    return run_sql(sql)

def get_tables_with_columns():
    tables = get_user_tables()
    print(f"User tables: {tables}")
    
    if isinstance(tables, dict) and "error" in tables:
        return tables

    table_columns = {}

    for table in tables:
        schema = get_table_schema(table)
        if "error" in schema:
            table_columns[table] = {"error": schema["error"]}
        else:
            # Extract only column names from schema rows
            cols = [row[1] for row in schema["rows"]]  # row[1] = column name
            table_columns[table] = cols

    return table_columns
