from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from core.config import settings
from services.user_service import get_or_create_user
from datetime import datetime

class AccessMiddleware(BaseMiddleware):
    def __init__(self, admin_only=False, approved_only=False):
        self.admin_only = admin_only
        self.approved_only = approved_only
        super().__init__()

    async def __call__(self, handler, event, data):
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        if user_id is None:
            return await handler(event, data)
        user = await get_or_create_user(user_id)
        # Автоматическая разблокировка, если есть comment с unblock_at
        if user.is_blocked and user.comment and user.comment.startswith("unblock_at:"):
            try:
                unblock_time = datetime.fromisoformat(user.comment.split(":", 1)[1])
                if datetime.utcnow() >= unblock_time:
                    # Снимаем блокировку
                    from services.user_service import update_user_status
                    await update_user_status(user.tg_id, is_blocked=False, comment=None)
                    # Уведомляем пользователя
                    if isinstance(event, Message):
                        await event.answer("Ваша временная блокировка снята. Вы снова можете пользоваться ботом! 🎉")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("Ваша временная блокировка снята. Вы снова можете пользоваться ботом! 🎉", show_alert=True)
                    user.is_blocked = False
                    user.comment = None
            except Exception:
                pass
        # Проверка блокировки
        if user.is_blocked:
            if isinstance(event, Message):
                await event.answer("Вы заблокированы. Обратитесь к администратору.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Вы заблокированы.", show_alert=True)
            return
        # Только для админов
        if self.admin_only and not (user.is_admin or user_id in settings.ADMIN_IDS):
            if isinstance(event, Message):
                await event.answer("Доступно только администраторам.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Доступно только администраторам.", show_alert=True)
            return
        # Только для одобренных
        if self.approved_only and not user.is_approved:
            if isinstance(event, Message):
                await event.answer("Доступно только после модерации.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Доступно только после модерации.", show_alert=True)
            return
        return await handler(event, data) 