from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.text2sql import build_text2sql
from app.sql_streamer import stream_select_query
from app.sql_to_db import execute_sql_query
from app.models import UserQuery, FinalResponse
from app.security_validator import SecurityException

app = FastAPI()

engine = build_text2sql()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.post("/process-text")
async def process_text_stream(req: UserQuery):
    """Обработка запроса с использованием production контракта"""
    query = req.natural_language_query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Field 'natural_language_query' is required")
    
    print(f"Received query from user {req.user_id}: {query}")

    try:
        # Используем новый пайплайн
        final_response: FinalResponse = await engine.process_user_request(req)
        
        sql_query = final_response.metadata.get("sql_query", final_response.content)
        
        if not sql_query:
            raise HTTPException(status_code=400, detail="Failed to generate SQL from the query")
        
        print("Generated SQL:", sql_query)
        
        # Выполняем запрос и получаем результат
        execution_result = await execute_sql_query(sql_query, query)
        
        # Формируем финальный ответ
        response_data = {
            "content": final_response.content,
            "output_format": final_response.output_format,
            "data": execution_result.data,
            "row_count": execution_result.row_count,
            "execution_time_ms": execution_result.execution_time_ms,
            "metadata": {
                **final_response.metadata,
                "execution_time_ms": execution_result.execution_time_ms,
                "row_count": execution_result.row_count
            }
        }
        
        return JSONResponse(content=response_data)
        
    except SecurityException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        print(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/process-text-stream")
async def process_text_stream_legacy(req: UserQuery):
    """Legacy endpoint для стриминга (обратная совместимость)"""
    query = req.natural_language_query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Field 'natural_language_query' is required")
    
    print(f"Received query from user {req.user_id}: {query}")

    try:
        # Используем новый пайплайн
        final_response: FinalResponse = await engine.process_user_request(req)
        
        sql_query = final_response.metadata.get("sql_query", final_response.content)
        
        if not sql_query:
            raise HTTPException(status_code=400, detail="Failed to generate SQL from the query")

        print("Generated SQL:", sql_query)
        
        # Используем стриминг для больших результатов
        return StreamingResponse(stream_select_query(sql_query), media_type="application/json")
        
    except SecurityException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        print(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
