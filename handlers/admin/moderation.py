from aiogram import Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.future import select
from core.db import async_session
from models.user import User
from keyboards.admin import moderation_keyboard
from keyboards.user import user_main_menu
from services.user_service import update_user_status
from core.config import settings
from aiogram import F

router = Router()

@router.callback_query(lambda c: c.data == "moderation")
async def open_moderation(call: CallbackQuery):
    await call.answer()
    await show_moderation(call.message)

@router.message(lambda m: m.text == "Модерация")
async def show_moderation(message: Message):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.is_approved == False, User.is_blocked == False))
        users = result.scalars().all()
        # Фильтруем заявки без ФИО и возраста
        users = [u for u in users if u.fio and u.age]
        if not users:
            await message.answer("Нет пользователей на модерации.")
            return
        for user in users:
            text = f"ФИО: {user.fio}\nВозраст: {user.age}"
            if user.passport_photo:
                await message.bot.send_photo(
                    message.chat.id,
                    user.passport_photo,
                    caption=text,
                    reply_markup=moderation_keyboard(user.tg_id)
                )
            else:
                await message.answer(text, reply_markup=moderation_keyboard(user.tg_id))

@router.callback_query(F.data.regexp(r"^approve_\d+$"))
async def approve_user(call: CallbackQuery, bot):
    tg_id = int(call.data.split("_")[1])
    await update_user_status(tg_id, is_approved=True)
    # Уведомление пользователю
    try:
        invite_text = "<b>🎉 Ваша заявка одобрена!</b> Добро пожаловать в бота!"
        if settings.WORKERS_CHAT_ID:
            # Для супергруппы ссылка формата https://t.me/c/2330703831
            chat_link = str(settings.WORKERS_CHAT_LINK)
            print(chat_link)
            invite_text += f"\n\nВас приглашают в рабочий чат! Присоединяйтесь: <b>{chat_link}</b>"
        await bot.send_message(tg_id, invite_text, reply_markup=user_main_menu(), parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        print(f"[approve_user] Ошибка отправки сообщения о принятии заявки пользователю {tg_id}: {e}")
    if call.message.photo or call.message.document:
        try:
            await call.message.delete()
        except Exception:
            pass
        await call.message.answer("Пользователь одобрен.")
    else:
        await call.message.edit_text("Пользователь одобрен.")

@router.callback_query(F.data.regexp(r"^reject_\d+$"))
async def reject_user(call: CallbackQuery, bot):
    tg_id = int(call.data.split("_")[1])
    await update_user_status(tg_id, is_approved=False, is_blocked=True)  # Блокируем повторную подачу
    # Уведомление пользователю
    try:
        await bot.send_message(tg_id, "Ваша заявка отклонена. Повторная подача невозможна.")
    except Exception:
        pass
    if call.message.photo or call.message.document:
        try:
            await call.message.delete()
        except Exception:
            pass
        await call.message.answer("Пользователь отклонён.")
    else:
        await call.message.edit_text("Пользователь отклонён.")

@router.message(F.text == "🛠 Админ-меню")
async def admin_menu_text(message: Message):
    from keyboards.admin import admin_main_menu
    await message.answer("Админ-меню:", reply_markup=admin_main_menu()) 