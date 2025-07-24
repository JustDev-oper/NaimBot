from aiogram import Router, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from services.user_service import get_or_create_user, update_user_status
from core.config import settings
from keyboards.user import user_main_menu
from keyboards.admin import admin_main_menu

router = Router()

class Registration(StatesGroup):
    fio = State()
    age = State()
    passport = State()

@router.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id)
    if user.is_admin or message.from_user.id in settings.ADMIN_IDS:
        from keyboards.admin import admin_reply_menu
        await message.answer("👑 <b>Добро пожаловать в админ-панель!</b>", reply_markup=admin_main_menu(), parse_mode="HTML")
        await message.answer("Для быстрого доступа используйте кнопку ниже.", reply_markup=admin_reply_menu())
        return
    if user.is_blocked:
        await message.answer("⛔️ <b>Вы заблокированы.</b> Обратитесь к администратору.", parse_mode="HTML")
        return
    if not user.is_approved:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="close_notify")]
        ])
        msg = await message.answer("<b>📋 Правила использования:</b>\n\nЯ подтверждаю, что мне есть <b>16 лет</b>. За ложные данные — <b>блокировка без оплаты</b>.\n\nПродолжая регистрацию, вы соглашаетесь с этими условиями. ⚠️", parse_mode="HTML", reply_markup=kb)
        reg_msg = await message.answer("<b>✍️ Введите ФИО:</b>", parse_mode="HTML")
        await state.set_state(Registration.fio)
        await state.update_data(reg_msg_id=reg_msg.message_id)
    else:
        from keyboards.user import user_main_menu, user_reply_menu
        await message.answer(f"👋 <b>Добро пожаловать, {user.fio or user.tg_id}!</b> Вы успешно вошли в бота!", reply_markup=user_main_menu(is_subscribed=user.is_subscribed), parse_mode="HTML")
        await message.answer("Для быстрого доступа используйте кнопку ниже. ⬇️", reply_markup=user_reply_menu())

@router.callback_query(F.data == "close_notify")
async def close_notify(call: CallbackQuery):
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.answer()

@router.message(Registration.fio)
async def reg_fio(message: Message, state: FSMContext):
    await state.update_data(fio=message.text)
    data = await state.get_data()
    try:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=data.get("reg_msg_id"),
            text=f"<b>✍️ ФИО:</b> {message.text}\n<b>🎂 Введите возраст:</b>",
            parse_mode="HTML"
        )
    except Exception:
        await message.answer("🎂 Введите возраст:")
    await state.set_state(Registration.age)

@router.message(Registration.age)
async def reg_age(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) < 16:
        data = await state.get_data()
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=data.get("reg_msg_id"),
                text="❗️ <b>Пожалуйста, введите возраст числом (от 16 и старше):</b>",
                parse_mode="HTML"
            )
        except Exception:
            await message.answer("❗️ Пожалуйста, введите возраст числом (от 16 и старше):")
        return
    await state.update_data(age=message.text)
    data = await state.get_data()
    try:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=data.get("reg_msg_id"),
            text=f"<b>✍️ ФИО:</b> {data.get('fio')}\n<b>🎂 Возраст:</b> {message.text}\n📸 <b>Пришлите фото паспорта с лицом:</b>",
            parse_mode="HTML"
        )
    except Exception:
        await message.answer("📸 Пришлите фото паспорта с лицом:")
    await state.set_state(Registration.passport)

@router.message(Registration.passport, F.photo)
async def reg_passport(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    await update_user_status(
        message.from_user.id,
        fio=data["fio"],
        age=int(data["age"]),
        passport_photo=photo_id,
        is_approved=False
    )
    try:
        from aiogram.types import InputMediaPhoto
        await message.bot.edit_message_media(
            chat_id=message.chat.id,
            message_id=data.get("reg_msg_id"),
            media=InputMediaPhoto(media=photo_id, caption="<b>Спасибо!</b> 🙏 Ваши данные отправлены на модерацию. Ожидайте решения. 🕓", parse_mode="HTML")
        )
    except Exception:
        await message.answer("<b>Спасибо!</b> 🙏 Ваши данные отправлены на модерацию. Ожидайте решения. 🕓", parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data == "subscribe_jobs")
async def subscribe_jobs(call: CallbackQuery):
    from services.user_service import update_user_status, get_or_create_user
    await update_user_status(call.from_user.id, is_subscribed=True)
    from keyboards.user import user_main_menu
    user = await get_or_create_user(call.from_user.id)
    try:
        await call.message.edit_text("🔔 <b>Вы подписались на уведомления о новых заданиях!</b>", reply_markup=user_main_menu(is_subscribed=True), parse_mode="HTML")
    except Exception:
        await call.message.answer("🔔 <b>Вы подписались на уведомления о новых заданиях!</b>", reply_markup=user_main_menu(is_subscribed=True), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "unsubscribe_jobs")
async def unsubscribe_jobs(call: CallbackQuery):
    from services.user_service import update_user_status, get_or_create_user
    await update_user_status(call.from_user.id, is_subscribed=False)
    from keyboards.user import user_main_menu
    user = await get_or_create_user(call.from_user.id)
    try:
        await call.message.edit_text("🔕 <b>Вы отписались от уведомлений о новых заданиях.</b>", reply_markup=user_main_menu(is_subscribed=False), parse_mode="HTML")
    except Exception:
        await call.message.answer("🔕 <b>Вы отписались от уведомлений о новых заданиях.</b>", reply_markup=user_main_menu(is_subscribed=False), parse_mode="HTML")
    await call.answer()

@router.message(F.text == "🏠 Главное меню")
async def main_menu_text(message: Message):
    from services.user_service import get_or_create_user
    from keyboards.user import user_main_menu
    user = await get_or_create_user(message.from_user.id)
    if not user.is_approved:
        await message.answer("Доступ к главному меню только после одобрения модератором.")
        return
    await message.answer("Главное меню:", reply_markup=user_main_menu(is_subscribed=user.is_subscribed))

@router.callback_query(F.data == "main_menu")
async def main_menu_cb(call: CallbackQuery):
    from services.user_service import get_or_create_user
    from keyboards.user import user_main_menu
    user = await get_or_create_user(call.from_user.id)
    if not user.is_approved:
        await call.answer("⛔️ Доступ к главному меню только после одобрения модератором.", show_alert=True)
        return
    try:
        await call.message.edit_text("🏠 <b>Главное меню:</b>", reply_markup=user_main_menu(is_subscribed=user.is_subscribed), parse_mode="HTML")
    except Exception:
        await call.message.answer("🏠 <b>Главное меню:</b>", reply_markup=user_main_menu(is_subscribed=user.is_subscribed), parse_mode="HTML")
    await call.answer() 