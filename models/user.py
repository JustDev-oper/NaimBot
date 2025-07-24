from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from models.base import Base
from datetime import datetime
from sqlalchemy import Text

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    tg_id = Column(Integer, unique=True)
    fio = Column(String(255))
    age = Column(Integer)
    passport_photo = Column(String(255))
    is_approved = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    referrer_id = Column(Integer)
    referrer = relationship("User", remote_side=[id])
    balance = Column(Integer, default=0)
    is_subscribed = Column(Boolean, default=True)
    comment = Column(String(255))

class BalanceHistory(Base):
    __tablename__ = "balance_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    change = Column(Integer)
    type = Column(String)  # пополнение, штраф, корректировка, вывод
    comment = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", backref="balance_history")

class AdminActionLog(Base):
    __tablename__ = "admin_action_log"
    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    action = Column(String)  # block, unblock, block_1d, etc
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow) 