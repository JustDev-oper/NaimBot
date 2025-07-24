import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.types import ErrorEvent
import logging
from core.config import settings
from core.db import async_session
from handlers.user import start as user_start
from handlers.user import profile as user_profile
from handlers.user import jobs as user_jobs
from handlers.admin import moderation as admin_moderation
from handlers.admin import users as admin_users
from handlers.admin import jobs as admin_jobs
from middlewares.access import AccessMiddleware


async def main():
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    @dp.errors()
    async def global_error_handler(event: ErrorEvent):
        try:
            if hasattr(event.update, 'message') and event.update.message:
                await event.update.message.answer('⚠️ Произошла ошибка. Пожалуйста, попробуйте позже.')
            elif hasattr(event.update, 'callback_query') and event.update.callback_query:
                await event.update.callback_query.message.answer('⚠️ Произошла ошибка. Пожалуйста, попробуйте позже.')
        except Exception:
            pass
        logging.exception('Ошибка в обработчике:', exc_info=event.exception)

    # Мидлвари
    dp.include_router(user_start.router)  # регистрация — без ограничений
    dp.include_router(user_profile.router).message.middleware(AccessMiddleware(approved_only=True))
    dp.include_router(user_jobs.router).message.middleware(AccessMiddleware(approved_only=True))
    dp.include_router(admin_moderation.router).message.middleware(AccessMiddleware(admin_only=True))
    dp.include_router(admin_users.router).message.middleware(AccessMiddleware(admin_only=True))
    dp.include_router(admin_jobs.router).message.middleware(AccessMiddleware(admin_only=True))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
