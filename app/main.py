from sqlalchemy import select
from db import ReadOnlyDB
from models import Transaction
import csv

db = ReadOnlyDB()

stmt = select(Transaction).where(Transaction.merchant_city == "Shymkent").limit(1)

with db.Session() as session:
    result = session.execute(stmt).scalars().all()  # вернёт только 1 запись
    if result:
        with open("shymkent_transactions3.csv", "w", newline='', encoding='utf-8') as csvfile:
            fieldnames = result[0].__table__.columns.keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow({col: getattr(result[0], col) for col in fieldnames})
