from sqlalchemy import create_engine, text
from sqlalchemy.engine import Result
import json
from datetime import date, datetime
from decimal import Decimal
from app.config import DATABASE_URL

# Оптимизированный engine с connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=20,  # Размер пула соединений
    max_overflow=10,  # Дополнительные соединения при нагрузке
    pool_pre_ping=True,  # Проверка соединений перед использованием
    pool_recycle=3600,  # Переиспользование соединений каждый час
    echo=False,  # Отключить логирование SQL
    future=True,
)

def json_default(obj):
    """Оптимизированная сериализация для JSON"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)

def stream_select_query(sql_query: str, batch_size: int = 10_000):
    """
    Оптимизированный генератор SELECT запросов.
    Стримит JSON массивы батчами с эффективной обработкой.
    """
    if not sql_query or not sql_query.strip().upper().startswith(("SELECT", "WITH")):
        raise ValueError("Only SELECT queries are allowed")

    with engine.connect() as conn:
        # Используем server-side cursor для эффективной потоковой обработки
        result: Result = conn.execution_options(
            stream_results=True,
            max_row_buffer=1000  # Буфер строк для оптимизации
        ).execute(text(sql_query))
        
        columns = list(result.keys())  # Преобразуем в список для быстрого доступа
        batch = []

        try:
            for row in result:
                # Оптимизированное создание словаря
                row_dict = dict(zip(columns, row))
                batch.append(row_dict)

                if len(batch) >= batch_size:
                    # Отдаём батч
                    yield json.dumps(batch, default=json_default, ensure_ascii=False) + "\n"
                    batch.clear()  # Очищаем список быстрее, чем создание нового

            # Отдаём остаток
            if batch:
                yield json.dumps(batch, default=json_default, ensure_ascii=False) + "\n"
        finally:
            # Гарантируем закрытие курсора
            result.close()
