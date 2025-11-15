# Mastercard Creathon Backend

Оптимизированный Text-to-SQL API сервер на FastAPI.

## Требования

- Python 3.9+
- PostgreSQL 16 (через Docker или локально)
- Google Gemini API ключ

## Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd mastercard-creathon-back
```

### 2. Создание виртуального окружения

**Windows:**

```powershell
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Установка зависимостей

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
# База данных PostgreSQL
DATABASE_URL=postgresql://user:pass@localhost:5432/mydb

# Google Gemini API
LLM_API_KEY=your_gemini_api_key_here
LLM_API_URL=https://generativelanguage.googleapis.com/v1beta
```

**Пример файла `.env.example` уже создан в проекте.**

### 5. Запуск PostgreSQL (если используете Docker)

```bash
docker-compose up -d
```

Проверьте, что PostgreSQL запущен:

```bash
docker ps
```

## Запуск сервера

### Способ 1: Через uvicorn напрямую

```bash
uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload
```

**Параметры:**

- `--host 0.0.0.0` - слушать на всех интерфейсах
- `--port 8000` - порт (по умолчанию 8000)
- `--reload` - автоматическая перезагрузка при изменении кода (только для разработки)

### Способ 2: Через Python модуль

```bash
python -m uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload
```

### Способ 3: Продакшн режим (без reload)

```bash
uvicorn app.server:app --host 0.0.0.0 --port 8000 --workers 4
```

**Параметры для продакшн:**

- `--workers 4` - количество worker процессов
- Убрать `--reload` для стабильности

### Способ 4: Через скрипт (Windows)

```powershell
.\run.bat
```

## Проверка работы

После запуска сервера откройте в браузере:

- **API документация (Swagger):** http://localhost:8000/docs
- **Альтернативная документация (ReDoc):** http://localhost:8000/redoc
- **Health check:** http://localhost:8000/health

## Использование API

### Основной endpoint

**POST** `/process-text`

**Тело запроса:**

```json
{
  "text": "Покажи все транзакции за последний месяц"
}
```

**Пример с curl:**

```bash
curl -X POST "http://localhost:8000/process-text" \
  -H "Content-Type: application/json" \
  -d '{"text": "Покажи все транзакции за последний месяц"}'
```

**Пример с Python:**

```python
import requests

response = requests.post(
    "http://localhost:8000/process-text",
    json={"text": "Покажи все транзакции за последний месяц"}
)

# Ответ приходит потоком (streaming)
for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
```

## Структура проекта

```
mastercard-creathon-back/
├── app/
│   ├── server.py          # FastAPI приложение
│   ├── config.py          # Конфигурация
│   ├── models.py          # SQLAlchemy модели
│   ├── db.py              # Работа с БД
│   ├── text2sql.py        # LLM генерация SQL
│   ├── sql_streamer.py    # Потоковая обработка SQL
│   ├── sql_validator.py   # Валидация SQL
│   └── sql_to_db.py       # Утилиты для SQL
├── requirements.txt       # Зависимости
├── docker-compose.yml     # Docker конфигурация
├── .env                   # Переменные окружения (создать)
└── README.md             # Этот файл
```

## Оптимизации

Проект оптимизирован для максимальной производительности:

- Connection pooling для БД
- Streaming ответов для больших результатов
- GZip сжатие
- SQL валидация и безопасность

Подробности в файле `OPTIMIZATION_NOTES.md`.

## Troubleshooting

### Ошибка подключения к БД

1. Проверьте, что PostgreSQL запущен:

   ```bash
   docker ps
   ```

2. Проверьте DATABASE_URL в `.env` файле

3. Проверьте доступность БД:
   ```bash
   psql -h localhost -U user -d mydb
   ```

### Ошибка с LLM API

1. Проверьте LLM_API_KEY в `.env` файле
2. Убедитесь, что ключ валидный и имеет доступ к Gemini API

### Порт уже занят

Используйте другой порт:

```bash
uvicorn app.server:app --host 0.0.0.0 --port 8001
```

## Разработка

Для разработки с автоматической перезагрузкой:

```bash
uvicorn app.server:app --reload --host 0.0.0.0 --port 8000
```

## Лицензия

См. файл LICENSE
