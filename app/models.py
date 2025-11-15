from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Numeric, TIMESTAMP

Base = declarative_base()

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(String, nullable=False)
    transaction_timestamp = Column(TIMESTAMP)
    card_id = Column(Integer)
    expiry_date = Column(String)
    issuer_bank_name = Column(String)
    merchant_id = Column(Integer)
    merchant_mcc = Column(Integer)
    mcc_category = Column(String)
    merchant_city = Column(String)
    transaction_type = Column(String)
    transaction_amount_kzt = Column(Numeric)
    original_amount = Column(Numeric, nullable=True)
    transaction_currency = Column(String)
    acquirer_country_iso = Column(String)
    pos_entry_mode = Column(String)
    wallet_type = Column(String)
