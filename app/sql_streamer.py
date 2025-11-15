from sqlalchemy import create_engine, text
import json
from app.config import DATABASE_URL

BATCH_SIZE = 100000

engine = create_engine(DATABASE_URL)

def stream_select_query(sql_query: str):
    """Генератор, отдающий результат SELECT батчами в формате JSON строк."""
    if not sql_query.strip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed")
    
    offset = 0
    while True:
        paginated_query = f"{sql_query.strip().rstrip(';')} OFFSET {offset}"
        
        with engine.connect() as conn:
            result = conn.execute(text(paginated_query))
            rows = result.fetchall()
            
            if not rows:
                break
            
            columns = result.keys()
            
            for row in rows:
                row_dict = {col: row[i] for i, col in enumerate(columns)}
                yield json.dumps(row_dict) + "\n"
            
            if len(rows) < BATCH_SIZE:
                break
            
            offset += BATCH_SIZE
