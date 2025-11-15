from sqlalchemy import select
from db import ReadOnlyDB
from models import Transaction
import csv

def get_shymkent():

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
    print("done")


def test_gemini():
    from google import genai

    # The client gets the API key from the environment variable `GEMINI_API_KEY`.
    client = genai.Client()

    response = client.models.generate_content(
        model="gemini-2.5-flash", contents="Explain how AI works in a few words"
    )
    print(response.text)

test_gemini()