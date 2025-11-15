import duckdb
import sqlalchemy

# Настройка подключения к PostgreSQL
engine = sqlalchemy.create_engine("postgresql://user:pass@localhost/mydb")
con = duckdb.connect()

parquet_file = "example_dataset.parquet"
chunk_size = 50000  # Размер пакета вставки

offset = 0
while True:
    # Читаем кусок из parquet
    chunk = con.execute(
        f"SELECT * FROM parquet_scan('{parquet_file}') LIMIT {chunk_size} OFFSET {offset}"
    ).df()

    if chunk.empty:
        print("Готово, все данные вставлены.")
        break

    # Вставка в PostgreSQL
    chunk.to_sql("transactions", engine, index=False, if_exists="append")

    offset += chunk_size
    print(f"Inserted {offset} rows…")
