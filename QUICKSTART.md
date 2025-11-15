# Быстрый старт

## 1. Установка зависимостей

```bash
# Активация виртуального окружения (если еще не активировано)
# Windows:
venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

## 2. Настройка .env файла

Создайте файл `.env` в корне проекта со следующим содержимым:

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/mydb
LLM_API_KEY=your_gemini_api_key_here
LLM_API_URL=https://generativelanguage.googleapis.com/v1beta
```

## 3. Запуск PostgreSQL (если нужно)

```bash
docker-compose up -d
```

## 4. Запуск сервера

### Вариант 1: Через uvicorn (рекомендуется)

```bash
uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload
```

### Вариант 2: Через скрипт

**Windows:**
```powershell
.\run.bat
```

**Linux/Mac:**
```bash
chmod +x run.sh
./run.sh
```

## 5. Проверка

Откройте в браузере: http://localhost:8000/docs

## Готово! 🚀

Сервер запущен и готов к работе.

