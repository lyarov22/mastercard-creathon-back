"""
Утилиты для валидации и очистки SQL запросов.
Оптимизировано для безопасности и производительности.
"""
import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Разрешенные SQL операции
ALLOWED_KEYWORDS = {
    'SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'LIMIT', 'OFFSET',
    'WITH', 'AS', 'AND', 'OR', 'NOT', 'IN', 'LIKE', 'ILIKE', 'BETWEEN',
    'IS', 'NULL', 'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'DISTINCT',
    'HAVING', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END'
}

# Запрещенные операции для безопасности
FORBIDDEN_KEYWORDS = {
    'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE',
    'EXEC', 'EXECUTE', 'GRANT', 'REVOKE', 'COMMIT', 'ROLLBACK'
}

def clean_sql(sql: str) -> str:
    """
    Очищает SQL от markdown блоков и лишних символов.
    Оптимизировано для быстрой обработки.
    """
    if not sql:
        return ""
    
    sql = sql.strip()
    
    # Удаляем markdown блоки
    if sql.startswith("```"):
        parts = sql.split("```")
        if len(parts) > 1:
            sql = parts[1]
            # Удаляем "sql" если есть
            if sql.startswith("sql"):
                sql = sql[3:]
            sql = sql.strip()
    
    # Удаляем лишние точки с запятой в конце
    sql = sql.rstrip(';').strip()
    
    return sql

def validate_sql(sql: str) -> Tuple[bool, str]:
    """
    Валидирует SQL запрос на безопасность.
    Возвращает (is_valid, error_message).
    """
    if not sql or not sql.strip():
        return False, "SQL query is empty"
    
    sql_upper = sql.upper()
    
    # Проверка на запрещенные операции
    for keyword in FORBIDDEN_KEYWORDS:
        # Используем word boundary для точного совпадения
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, sql_upper):
            logger.warning(f"Blocked forbidden keyword: {keyword}")
            return False, f"Forbidden operation: {keyword}"
    
    # Проверка что это SELECT или WITH запрос
    if not sql_upper.strip().startswith(("SELECT", "WITH")):
        return False, "Only SELECT and WITH queries are allowed"
    
    # Базовая проверка структуры
    if sql_upper.count("SELECT") > 5:  # Защита от слишком сложных запросов
        return False, "Query is too complex"
    
    return True, ""

def sanitize_and_validate(sql: str) -> Tuple[str, bool, str]:
    """
    Очищает и валидирует SQL запрос.
    Возвращает (cleaned_sql, is_valid, error_message).
    """
    cleaned = clean_sql(sql)
    is_valid, error = validate_sql(cleaned)
    return cleaned, is_valid, error

