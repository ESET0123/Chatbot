import sqlite3

conn = sqlite3.connect("mydata.db")
cur = conn.cursor()

# List all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cur.fetchall()
print("Tables:", tables)

# Fetch data from 'users'
cur.execute("SELECT * FROM forecasted_table;")
rows = cur.fetchall()
for row in rows:
    print(row)

conn.close()



# import sqlite3
# import pandas as pd
# import random
# from datetime import datetime, timedelta
 
# DB_PATH = "mydata.db"
 
# # ---- CONNECT ----
# conn = sqlite3.connect(DB_PATH)
# cur = conn.cursor()
 
# # ---- DROP if exists ----
# cur.execute("DROP TABLE IF EXISTS forecasted_table")
 
# # ---- CREATE TABLE ----
# cur.execute(
#     """
#     CREATE TABLE forecasted_table (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         meter_id TEXT NOT NULL,
#         datetime TEXT NOT NULL,
#         forecasted_load_kwh REAL
#     )
#     """
# )
 
# # ------------ Create dummy realistic data ----------
# num_rows = 2000
 
# # suppose 3 real meters
# meter_ids = ["MTR_1001", "MTR_1002", "MTR_1003"]
 
# start_time = datetime(2025,12,1,0,0,0)
 
# records = []
 
# for i in range(num_rows):
#     meter = random.choice(meter_ids)
 
#     # time increments by 15 minutes like real smart meter systems
#     dt = start_time + timedelta(minutes=15*i)
 
#     # load values: realistic 1–8 kWh per 15 min period
#     load = round(random.uniform(1.2, 7.8), 2)
 
#     records.append((meter, dt.strftime("%Y-%m-%d %H:%M:%S"), load))
 
 
# df = pd.DataFrame(records, columns=["meter_id","datetime","forecasted_load_kwh"])
 
# # write into DB
# df.to_sql("forecasted_table", conn, if_exists="append", index=False)
 
# conn.commit()
# conn.close()
 
# print(f"Created {DB_PATH} with table 'forecasted_table' and {num_rows} rows.")