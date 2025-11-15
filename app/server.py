from fastapi import FastAPI, HTTPException, Query
from app.test_sql_generator import generate_sql  # импортируем твою функцию

app = FastAPI()

@app.get("/process-text")
def process_text(text: str = Query(..., description="Текст для обработки")):
    try:
        result = generate_sql(text)  # вызываем твою функцию
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
