from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from app.text2sql import build_text2sql
from app.sql_streamer import stream_select_query
from app.sql_validator import sanitize_and_validate
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Mastercard Creathon API",
    description="Optimized Text-to-SQL API",
    version="1.0.0"
)

# Инициализация engine один раз при старте приложения
engine = build_text2sql()

# Middleware для оптимизации
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# GZip compression для уменьшения размера ответов
app.add_middleware(GZipMiddleware, minimum_size=1000)

class TextRequest(BaseModel):
    text: str

@app.post("/process-text")
async def process_text_stream(req: TextRequest):
    """
    Оптимизированный endpoint для обработки текстовых запросов и генерации SQL.
    """
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Field 'text' is required")
    
    logger.info(f"Received text query: {text[:100]}...")

    try:
        sql = engine.generate(text)
        logger.info(f"Generated SQL: {sql[:200]}...")
        
        if not sql or not sql.strip():
            raise HTTPException(
                status_code=400, 
                detail="Failed to generate SQL from the text"
            )

        # Очистка и валидация SQL
        cleaned_sql, is_valid, error_msg = sanitize_and_validate(sql)
        
        if not is_valid:
            logger.warning(f"SQL validation failed: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid SQL query: {error_msg}"
            )
        
        return StreamingResponse(
            stream_select_query(cleaned_sql), 
            media_type="application/json",
            headers={
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-cache"
            }
        )
    except ValueError as e:
        logger.error(f"SQL validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
