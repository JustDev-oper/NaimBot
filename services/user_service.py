from sqlalchemy.future import select
from models.user import User
from core.db import async_session

async def get_or_create_user(tg_id: int):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(tg_id=tg_id)
            session.add(user)
            await session.commit()
        return user

async def update_user_status(tg_id: int, **kwargs):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            for k, v in kwargs.items():
                setattr(user, k, v)
            await session.commit()
        return user 