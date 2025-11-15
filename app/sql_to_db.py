import re
import time
from typing import List, Dict, Any, Optional
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import create_engine, text
from app.config import DATABASE_URL
from app.models import ExecutionResult
from app.security_validator import SecurityValidator, SecurityException

BATCH_SIZE = 50000  # Максимальный размер батча
MAX_RESULT_ROWS = 10000  # Максимальное количество строк результата

security_validator = SecurityValidator()


def _convert_to_json_serializable(value: Any) -> Any:
    """
    Преобразует значение в JSON-совместимый тип.
    Обрабатывает Decimal, datetime, date и другие типы.
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (int, float, str, bool)):
        return value
    # Для других типов преобразуем в строку
    return str(value)


def _is_select_query(sql_query: str) -> bool:
    """Проверяет, является ли запрос SELECT запросом."""
    return sql_query.strip().upper().startswith(("SELECT", "WITH"))


def _has_limit_in_query(sql_query: str) -> bool:
    """
    Проверяет, есть ли LIMIT в SQL запросе (включая подзапросы).
    Если есть LIMIT, батчинг может нарушить логику запроса.
    """
    query_upper = sql_query.upper()
    # Ищем любое вхождение LIMIT
    return bool(re.search(r'\bLIMIT\s+\d+', query_upper, re.IGNORECASE))


def _extract_limit_from_query(sql_query: str) -> Optional[int]:
    """
    Извлекает значение последнего (внешнего) LIMIT из SQL запроса.
    Если LIMIT есть в подзапросе, это тоже важно - батчинг может нарушить логику.
    """
    query_upper = sql_query.upper()
    
    # Ищем все LIMIT в запросе
    limit_matches = list(re.finditer(r'\bLIMIT\s+(\d+)', query_upper, re.IGNORECASE))
    if not limit_matches:
        return None
    
    # Берем последний LIMIT (самый внешний, если есть)
    # Если LIMIT только в подзапросе, все равно берем его значение
    last_limit = limit_matches[-1]
    limit_value = int(last_limit.group(1))
    return limit_value


def _add_limit_offset(sql_query: str, limit: int, offset: int) -> str:
    """
    Добавляет или модифицирует LIMIT и OFFSET в SQL запросе.
    """
    # Удаляем существующие LIMIT и OFFSET
    query_upper = sql_query.upper()
    
    # Находим позицию последнего LIMIT
    limit_match = list(re.finditer(r'\bLIMIT\s+\d+', query_upper, re.IGNORECASE))
    if limit_match:
        last_limit = limit_match[-1]
        # Удаляем LIMIT и возможный OFFSET после него
        start_pos = last_limit.start()
        # Ищем OFFSET после LIMIT
        remaining = sql_query[start_pos:]
        offset_match = re.search(r'\s+OFFSET\s+\d+', remaining, re.IGNORECASE)
        if offset_match:
            end_pos = start_pos + offset_match.end()
            sql_query = sql_query[:start_pos] + sql_query[end_pos:]
        else:
            sql_query = sql_query[:start_pos] + sql_query[last_limit.end():]
    
    # Добавляем новые LIMIT и OFFSET
    sql_query = sql_query.rstrip().rstrip(';')
    return f"{sql_query} LIMIT {limit} OFFSET {offset}"


async def execute_sql_query(sql_query: str, user_intent: str = "") -> ExecutionResult:
    """
    Выполняет SQL запрос с валидацией и возвращает ExecutionResult.
    Оптимизировано для больших результатов: обрабатывает батчами.
    
    Args:
        sql_query: SQL запрос в виде строки
        user_intent: Оригинальный запрос пользователя для валидации
        
    Returns:
        ExecutionResult с данными и метаинформацией
    """
    start_time = time.time()
    engine = create_engine(DATABASE_URL)
    
    # Валидация безопасности перед выполнением
    validation = security_validator.validate_sql(sql_query, user_intent)
    if not validation.is_safe:
        raise SecurityException(f"Query violates security policy: {validation.validation_notes}")
    
    with engine.connect() as connection:
        # Проверяем, есть ли в запросе LIMIT (включая подзапросы)
        has_limit = _has_limit_in_query(sql_query)
        query_limit = _extract_limit_from_query(sql_query)
        
        # Если есть LIMIT, выполняем запрос без батчинга
        # Это важно для запросов типа "топ-10", где LIMIT должен строго соблюдаться
        # Также важно для запросов с LIMIT в подзапросе - батчинг может нарушить логику
        if has_limit:
            try:
                result = connection.execute(text(sql_query))
                columns = list(result.keys())
                rows = result.fetchall()
                
                # Преобразуем в словари с JSON-совместимыми значениями
                all_data: List[Dict[str, Any]] = []
                for row in rows:
                    row_dict = {
                        col: _convert_to_json_serializable(row[i]) 
                        for i, col in enumerate(columns)
                    }
                    all_data.append(row_dict)
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                return ExecutionResult(
                    data=all_data,
                    row_count=len(all_data),
                    execution_time_ms=execution_time_ms
                )
            except Exception as e:
                raise Exception(f"SQL execution error: {str(e)}")
        
        # Для запросов без LIMIT или с большим LIMIT используем батчинг
        all_data: List[Dict[str, Any]] = []
        offset = 0
        total_rows = 0
        
        while True:
            # Формируем запрос с LIMIT и OFFSET
            paginated_query = _add_limit_offset(sql_query, BATCH_SIZE, offset)
            
            try:
                result = connection.execute(text(paginated_query))
                
                # Получаем колонки только один раз
                if offset == 0:
                    columns = list(result.keys())
                
                # Получаем батч результатов
                rows = result.fetchall()
                
                if not rows:
                    break
                
                # Преобразуем в словари с JSON-совместимыми значениями
                for row in rows:
                    row_dict = {
                        col: _convert_to_json_serializable(row[i]) 
                        for i, col in enumerate(columns)
                    }
                    all_data.append(row_dict)
                
                total_rows += len(rows)
                
                # Ограничение на максимальное количество строк
                if total_rows >= MAX_RESULT_ROWS:
                    all_data = all_data[:MAX_RESULT_ROWS]
                    break
                
                # Если получили меньше записей, чем запрашивали, значит это последний батч
                if len(rows) < BATCH_SIZE:
                    break
                
                offset += BATCH_SIZE
                
            except Exception as e:
                raise Exception(f"SQL execution error: {str(e)}")
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        return ExecutionResult(
            data=all_data,
            row_count=len(all_data),
            execution_time_ms=execution_time_ms
        )


def execute_sql_query_sync(sql_query: str):
    """
    Синхронная версия для обратной совместимости.
    Выполняет SQL запрос и выводит результат в консоль.
    """
    import asyncio
    try:
        result = asyncio.run(execute_sql_query(sql_query))
        
        if not result.data:
            print("Нет данных для отображения.")
            return
        
        # Выводим заголовки
        if result.data:
            columns = list(result.data[0].keys())
            print(" | ".join(columns))
            print("-" * 80)
            
            # Выводим данные
            for row in result.data:
                row_values = [str(value) if value is not None else "NULL" for value in row.values()]
                print(" | ".join(row_values))
        
        print(f"\n{'='*80}")
        print(f"Всего строк: {result.row_count:,}")
        print(f"Время выполнения: {result.execution_time_ms:.2f} мс")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"Ошибка выполнения запроса: {e}")


