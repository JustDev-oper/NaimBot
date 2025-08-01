from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, BigInteger
from sqlalchemy.orm import relationship
from models.base import Base
from datetime import datetime
from sqlalchemy import Text

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True)
    fio = Column(String(255))
    age = Column(Integer)
    passport_photo = Column(String(255))
    is_approved = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    balance = Column(Integer, default=0)
    is_subscribed = Column(Boolean, default=True)
    comment = Column(String(255))

class BalanceHistory(Base):
    __tablename__ = "balance_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    change = Column(Integer)
    type = Column(String(255))  # пополнение, штраф, корректировка, вывод
    comment = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", backref="balance_history")

class AdminActionLog(Base):
    __tablename__ = "admin_action_log"
    id = Column(Integer, primary_key=True)
    admin_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    action = Column(String(255))  # block, unblock, block_1d, etc
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow) 