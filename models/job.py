from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from models.base import Base

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    pay = Column(Integer)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    photo = Column(String(255))
    workers_needed = Column(Integer)
    workers = Column(String(255), default="")  # id через запятую
    min_age = Column(Integer, default=16)
    max_age = Column(Integer, default=99)
    address = Column(String(255), default="")
    group_message_id = Column(Integer, nullable=True) 