from models.base import Base
from models.user import User
from models.job import Job
from core.db import engine
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

async def create_tables():
    print(f"Создание таблиц в БД: {os.getenv('DB_NAME', 'не указано')}...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Таблицы успешно созданы!")

if __name__ == "__main__":
    asyncio.run(create_tables())