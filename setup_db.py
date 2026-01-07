
import pymysql
import os
from config import Config

def setup_database():
    print("Connecting to MySQL server...")
    # Connect without selecting DB first
    conn = pymysql.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD
    )
    cursor = conn.cursor()
    
    db_name = Config.MYSQL_DB
    
    print(f"Creating database '{db_name}' if it doesn't exist...")
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
    conn.select_db(db_name)
    
    print("Reading schema.sql...")
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    if not os.path.exists(schema_path):
        print(f"Error: schema.sql not found at {schema_path}")
        return
        
    with open(schema_path, 'r') as f:
        schema = f.read()
        
    print("Executing schema statements...")
    # Split queries by semicolon and execute them
    queries = schema.split(';')
    for query in queries:
        if query.strip():
            try:
                cursor.execute(query)
            except Exception as e:
                print(f"Warning executing query: {e}")
                
    conn.commit()
    cursor.close()
    conn.close()
    print("Database setup complete!")

if __name__ == "__main__":
    setup_database()
