from sqlalchemy import create_engine, text
import json
from datetime import date, datetime
from decimal import Decimal
from app.config import DATABASE_URL

BATCH_SIZE = 100_000

engine = create_engine(DATABASE_URL)

def json_default(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)  # всё остальное приводим к строке

def stream_select_query(sql_query: str):
    """Генератор, отдающий результат SELECT батчами в формате JSON массивов."""
    if not sql_query or not sql_query.strip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed")

    offset = 0
    while True:
        paginated_query = f"{sql_query.strip().rstrip(';')} OFFSET {offset} LIMIT {BATCH_SIZE}"

        with engine.connect() as conn:
            result = conn.execute(text(paginated_query))
            rows = result.fetchall()
            
            if not rows:
                break

            columns = result.keys()
            batch = [
                {col: row[i] for i, col in enumerate(columns)}
                for row in rows
            ]

            # Отдаём весь батч сразу как JSON массив, приводя все даты/decimal к строкам/числам
            yield json.dumps(batch, default=json_default) + "\n"

            if len(rows) < BATCH_SIZE:
                break

            offset += BATCH_SIZE
