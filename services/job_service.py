from sqlalchemy.future import select
from sqlalchemy import update
from models.job import Job
from models.user import User
from core.db import async_session
from datetime import datetime

async def create_job(title, description, pay, start_time, end_time, min_age, max_age, address, photo, workers_needed):
    async with async_session() as session:
        job = Job(
            title=title,
            description=description,
            pay=pay,
            start_time=start_time,
            end_time=end_time,
            min_age=min_age,
            max_age=max_age,
            address=address,
            photo=photo,
            workers_needed=workers_needed
        )
        session.add(job)
        await session.commit()
        return job

async def get_jobs():
    async with async_session() as session:
        result = await session.execute(select(Job))
        return result.scalars().all()

async def get_job(job_id):
    async with async_session() as session:
        result = await session.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

async def apply_for_job(job_id, user_id):
    async with async_session() as session:
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return False
        ids = set(map(int, job.workers.split(","))) if job.workers else set()
        if user_id in ids:
            return False
        if len(ids) >= job.workers_needed:
            return False
        ids.add(user_id)
        job.workers = ",".join(map(str, ids))
        await session.commit()
        return True 