from models.base import Base
from models.user import User
from models.job import Job
from core.db import engine
import asyncio

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(create_tables())