import json
from typing import List, Optional
from google import genai
from google.genai import types

from app.config import LLM_API_KEY
from app.models import (
    UserQuery, FormatDecision, SQLValidation, ExecutionResult, FinalResponse
)
from app.security_validator import SecurityValidator, SecurityException

client = genai.Client(api_key=LLM_API_KEY)

TABLE_SCHEMA = {
    "id": "Integer primary key",
    "transaction_id": "String transaction identifier",
    "transaction_timestamp": "Timestamp of transaction",
    "card_id": "Integer card identifier",
    "expiry_date": "String card expiry date",
    "issuer_bank_name": "String issuer bank name",
    "merchant_id": "Integer merchant identifier",
    "merchant_mcc": "Integer merchant mcc code",
    "mcc_category": "String mcc category. Only this values: (Clothing & Apparel, Dining & Restaurants, Electronics & Software, Fuel & Service Stations, General Retail & Department, Grocery & Food Markets, Hobby, Books, Sporting Goods, Home Furnishings & Supplies, Pharmacies & Health, Services (Other), Travel & Transportation, Unknown, Utilities & Bill Payments)",
    "merchant_city": "String merchant city. Example: (Astana, Almaty, Shymkent, Other)",
    "transaction_type": "String type of transaction. Example: (ATM_WITHDRAWAL, BILL_PAYMENT, ECOM, P2P_IN, P2P_OUT, POS, SALARY)",
    "transaction_amount_kzt": "Numeric amount in KZT",
    "original_amount": "Numeric original amount",
    "transaction_currency": "String currency in ISO format. Example: (ARM, BLR, CHN, GEO, ITA, KAZ, KGZ, TUR, USA, UZB)",
    "acquirer_country_iso": "String acquirer ISO. Example: ()",
    "pos_entry_mode": "String pos entry mode. Only this values: (Chip, QR_Code, Contactless, Swipe)",
    "wallet_type": "String wallet type. Only this values: (Bank's QR, Samsung Pay, Google Pay, Apple Pay)"
}

DEFAULT_LIMIT = 1000
AGGREGATION_THRESHOLD = 10000
MAX_RETRIES = 3

PRODUCTION_SYSTEM_PROMPT = f"""
SYSTEM_ROLES:
- Data Analyst Assistant
- SQL Query Optimizer  
- Security Validator
- Result Formatter

GOLDEN_RULES:
1. SCHEMA_COMPLIANCE: Строго соблюдай TABLE_SCHEMA и типы данных
2. READ_ONLY: Только SELECT запросы. Запрещены: UPDATE, DELETE, DROP, ALTER, CREATE, INSERT
3. SECURITY_FIRST: Если запрос рискован - отклони и объясни
4. CONTEXT_AWARENESS: При недостатке контекста - запроси уточнение
5. PERFORMANCE: Оптимизируй SQL (индексы, WHERE перед JOIN, LIMIT)
6. VALIDATION_LOOP: Проверяй соответствие на каждом этапе
7. TYPE_SAFETY: Все данные строго типизированы

POSTGRES_OPTIMIZATION:
- Используй EXPLAIN ANALYZE для сложных запросов
- Применяй индексные подсказки (merchant_city, transaction_timestamp)
- Ограничивай результат LIMIT {DEFAULT_LIMIT} если не указано иное
- Используй WITH для сложных агрегаций

ERROR_HANDLING:
- SQL_ERROR -> повторная генерация (макс. {MAX_RETRIES} попытки)
- NO_DATA -> понятное сообщение пользователю
- TIMEOUT -> упрощение запроса

All data in the database is stored in English. For example, city names, bank names, MCC categories, transaction types, currencies are all in English.
If the user speaks Russian or Kazakh, translate their intent to English values where appropriate. 
Always output SQL in English syntax and using English values.
Use table 'transactions'. Use lowercase column names.
Dates filtered through transaction_timestamp.
Amounts filtered through transaction_amount_kzt.
String filters must use ILIKE.

Table schema:
{json.dumps(TABLE_SCHEMA, indent=2)}
"""

class ProductionLLMContract:
    """Production-ready контракт для обработки запросов с валидацией"""
    
    def __init__(self):
        self.model = "gemini-2.5-flash"
        self.security_validator = SecurityValidator()
        self.table_schema = TABLE_SCHEMA
    
    def _call_gemini(self, system_instruction: str, user_text: str) -> str:
        """Вызов Gemini API (сохраняем оригинальную логику)"""
        contents = types.Content(
            role="user",
            parts=[types.Part.from_text(text=system_instruction), types.Part.from_text(text=user_text)]
        )
        config = types.GenerateContentConfig(
            system_instruction=None,
            temperature=0.0,
            max_output_tokens=5000
        )
        response = client.models.generate_content(
            model=self.model,
            contents=[contents],
            config=config
        )
        print("Gemini response received")
        return response.text
    
    async def _determine_output_format(self, user_query: UserQuery) -> FormatDecision:
        """Определение формата вывода"""
        prompt = f"""
        Определи формат вывода для запроса пользователя.
        
        USER_QUERY: {user_query.natural_language_query}
        
        Возможные форматы:
        - "text": текстовый ответ, статистика, описания
        - "table": табличные данные, списки транзакций
        - "graph": данные для графиков (временные ряды, сравнения)
        - "diagram": диаграммы, распределения
        
        Верни JSON:
        {{
            "output_format": "text|table|graph|diagram",
            "confidence_score": 0.0-1.0,
            "clarification_question": "null или вопрос для уточнения",
            "refined_query": "уточненный запрос пользователя"
        }}
        """
        
        response = self._call_gemini(PRODUCTION_SYSTEM_PROMPT, prompt)
        try:
            result = json.loads(response)
            return FormatDecision(**result)
        except:
            # Fallback на table формат
            return FormatDecision(
                output_format="table",
                confidence_score=0.7,
                clarification_question=None,
                refined_query=user_query.natural_language_query
            )
    
    async def _load_relevant_examples(self, output_format: str, query: str) -> List:
        """Загрузка релевантных примеров (заглушка, можно расширить)"""
        return []
    
    async def _generate_and_validate_sql(
        self, 
        query: str, 
        examples: List,
        retry_count: int = 0
    ) -> SQLValidation:
        """Генерация SQL с многоуровневой валидацией"""
        prompt = f"""
        USER_QUERY: {query}
        SCHEMA: {json.dumps(self.table_schema, indent=2)}
        EXAMPLES: {examples}
        
        Generate optimized PostgreSQL SELECT query:
        - Use indexes on merchant_city, transaction_timestamp  
        - Add WHERE conditions before JOINs
        - Include LIMIT {DEFAULT_LIMIT} if aggregating large datasets
        - Validate against user intent
        - Only SELECT queries allowed
        
        Return JSON:
        {{
            "sql_query": "string",
            "explanation": "string",
            "estimated_performance": "good|medium|poor"
        }}
        """
        
        try:
            response = self._call_gemini(PRODUCTION_SYSTEM_PROMPT, prompt)
            
            # Парсим JSON ответ
            sql_query = None
            
            # Пытаемся найти JSON блок в ответе
            response_clean = response.strip()
            
            # Убираем префикс "json" если ответ начинается с него
            if response_clean.lower().startswith("json"):
                # Пропускаем слово "json" и следующий пробел/перенос строки
                lines = response_clean.split("\n")
                if lines[0].strip().lower() == "json":
                    response_clean = "\n".join(lines[1:]).strip()
                else:
                    response_clean = response_clean[4:].strip()
            
            # Убираем markdown обёртки если есть
            if response_clean.startswith("```"):
                parts = response_clean.split("```")
                if len(parts) >= 3:
                    json_part = parts[1]
                    if json_part.startswith("json"):
                        json_part = json_part[4:].strip()
                    response_clean = json_part.strip()
            
            # Пытаемся найти JSON объект в тексте
            json_start = response_clean.find("{")
            json_end = response_clean.rfind("}")
            
            if json_start != -1 and json_end != -1 and json_end > json_start:
                json_str = response_clean[json_start:json_end + 1]
                try:
                    result = json.loads(json_str)
                    sql_query = result.get("sql_query", None)
                    if sql_query:
                        print(f"Extracted SQL from JSON: {sql_query[:100]}...")
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    pass
            
            # Если не нашли в JSON, пытаемся извлечь SQL напрямую
            if not sql_query:
                # Ищем SELECT или WITH в ответе
                sql_keywords = ["SELECT", "WITH"]
                for keyword in sql_keywords:
                    idx = response_clean.upper().find(keyword)
                    if idx != -1:
                        # Берем текст начиная с ключевого слова до конца или до следующего блока
                        potential_sql = response_clean[idx:]
                        # Убираем возможные завершающие символы после SQL
                        if ";" in potential_sql:
                            sql_query = potential_sql[:potential_sql.index(";") + 1]
                        else:
                            sql_query = potential_sql.split("\n")[0] if "\n" in potential_sql else potential_sql
                        break
            
            # Если все еще не нашли, берем весь ответ
            if not sql_query:
                sql_query = response_clean
                # Убираем префикс "json" если есть (уже обработано выше, но на всякий случай)
                if sql_query.lower().startswith("json"):
                    sql_query = sql_query[4:].strip()
            
            if not sql_query:
                raise ValueError("Could not extract SQL query from Gemini response")
            
            # Финальная очистка
            sql_query = sql_query.strip()
            if sql_query.startswith("```"):
                sql_query = sql_query.split("```")[1]
                if sql_query.startswith("sql"):
                    sql_query = sql_query[3:]
                sql_query = sql_query.strip()
            
            # Убираем точку с запятой в конце если есть (для валидации)
            sql_query_clean = sql_query.rstrip(";").strip()
            
            print(f"Final extracted SQL: {sql_query_clean[:200]}...")
            
            # Валидация безопасности
            validation = self.security_validator.validate_sql(sql_query_clean, query)
            
            # Если небезопасен и есть попытки - регенерируем
            if not validation.is_safe and retry_count < MAX_RETRIES:
                return await self._generate_and_validate_sql(query, examples, retry_count + 1)
            
            return validation
            
        except Exception as e:
            print(f"Error generating SQL: {e}")
            return SQLValidation(
                sql_query="",
                is_safe=False,
                matches_intent=False,
                validation_notes=f"Ошибка генерации: {str(e)}",
                alternative_query=None
            )
    
    async def _regenerate_sql_with_feedback(self, sql_validation: SQLValidation) -> SQLValidation:
        """Регенерация SQL с учетом обратной связи"""
        # Упрощенная реализация - можно улучшить
        return sql_validation
    
    def _build_clarification_response(self, format_decision: FormatDecision) -> FinalResponse:
        """Построение ответа с запросом уточнения"""
        return FinalResponse(
            content=format_decision.clarification_question or "Требуется уточнение запроса",
            output_format=format_decision.output_format,
            data_preview=None,
            metadata={"requires_clarification": True}
        )
    
    async def process_user_request(self, user_query: UserQuery) -> FinalResponse:
        """Основной пайплайн обработки запроса"""
        # Шаг 1: Определение формата с валидацией
        format_decision = await self._determine_output_format(user_query)
        
        if format_decision.clarification_question:
            return self._build_clarification_response(format_decision)
        
        # Шаг 2: Поиск примеров и генерация SQL
        examples = await self._load_relevant_examples(
            format_decision.output_format, 
            format_decision.refined_query
        )
        
        # Шаг 3: Валидация SQL (безопасность + соответствие)
        sql_validation = await self._generate_and_validate_sql(
            format_decision.refined_query, 
            examples
        )
        
        if not sql_validation.is_safe:
            raise SecurityException(f"Query violates security policy: {sql_validation.validation_notes}")
            
        if not sql_validation.matches_intent:
            sql_validation = await self._regenerate_sql_with_feedback(sql_validation)
        
        # Возвращаем SQL для выполнения (выполнение будет в sql_to_db.py)
        return FinalResponse(
            content=sql_validation.sql_query,
            output_format=format_decision.output_format,
            data_preview=None,
            metadata={
                "sql_query": sql_validation.sql_query,
                "validation_notes": sql_validation.validation_notes
            }
        )
    
    def generate(self, nl_query: str) -> str:
        """Простой метод для обратной совместимости"""
        user_query = UserQuery(natural_language_query=nl_query, user_id="default")
        import asyncio
        result = asyncio.run(self.process_user_request(user_query))
        return result.metadata.get("sql_query", result.content)

def build_text2sql():
    return ProductionLLMContract()
