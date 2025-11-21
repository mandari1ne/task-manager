import time
import psycopg2
import os

db = {
    'dbname': os.getenv('POSTGRES_DB'),
    'user': os.getenv('POSTGRES_USER'),
    'password': os.getenv('POSTGRES_PASSWORD'),
    'host': os.getenv('POSTGRES_HOST'),
    'port': os.getenv('POSTGRES_PORT', 5432),
}

while True:
    try:
        conn = psycopg2.connect(**db)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM manager_task LIMIT 1;")
        cursor.close()
        conn.close()
        break
    except Exception:
        print("Database not ready, waiting...")
        time.sleep(3)
