from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from services.user_service import get_or_create_user, update_user_status
from keyboards.user import user_main_menu, user_profile_keyboard, user_reply_menu
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from models.user import BalanceHistory
from core.db import async_session
from datetime import datetime, timedelta
from core.config import settings

router = Router()

class EditProfile(StatesGroup):
    fio = State()
    age = State()

class WithdrawFSM(StatesGroup):
    amount = State()
    requisites = State()
    confirm = State()

@router.callback_query(F.data == "profile")
async def show_profile_cb(call: CallbackQuery, state: FSMContext):
    user = await get_or_create_user(call.from_user.id)
    from sqlalchemy import select
    from datetime import datetime, timedelta
    async with async_session() as session:
        result = await session.execute(
            select(BalanceHistory)
            .where(BalanceHistory.user_id == user.id, BalanceHistory.type == "вывод")
            .order_by(BalanceHistory.created_at.desc())
        )
        history = result.scalars().all()
    now = datetime.utcnow()
    for row in history:
        async with async_session() as session2:
            cancel_result = await session2.execute(
                select(BalanceHistory)
                .where(BalanceHistory.user_id == row.user_id, BalanceHistory.type == "отмена вывода", BalanceHistory.change == abs(row.change))
            )
            cancel_hist = cancel_result.scalar_one_or_none()
            if cancel_hist:
                continue
        if (now - row.created_at).total_seconds() > 86400:
            try:
                await call.message.edit_text("<b>⏰ Напоминание:</b> Ваша заявка на вывод <b>ещё не рассмотрена</b>. Если это займёт больше времени, обратитесь к администратору.", parse_mode="HTML")
            except Exception:
                await call.message.answer("<b>⏰ Напоминание:</b> Ваша заявка на вывод <b>ещё не рассмотрена</b>. Если это займёт больше времени, обратитесь к администратору.", parse_mode="HTML")
            break
    text = f"<b>👤 Ваш профиль</b>\n\n<b>ФИО:</b> {user.fio or '—'}\n<b>Возраст:</b> {user.age or '—'}\n<b>💰 Баланс:</b> <b>{user.balance} ₽</b>"
    kb = user_profile_keyboard()
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await call.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "withdraw")
async def withdraw_request(call: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    try:
        await call.message.edit_text("💸 <b>Введите сумму для вывода:</b>", reply_markup=kb, parse_mode="HTML")
    except Exception:
        await call.message.answer("💸 <b>Введите сумму для вывода:</b>", reply_markup=kb, parse_mode="HTML")
    await state.set_state(WithdrawFSM.amount)
    await call.answer()

@router.message(WithdrawFSM.amount)
async def withdraw_amount(message: Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id)
    if not message.text.isdigit() or int(message.text) <= 0:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="profile"), InlineKeyboardButton(text="❌ Закрыть", callback_data="close_notify")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        await message.edit_text("❗️ <b>Введите корректную сумму:</b>", reply_markup=kb, parse_mode="HTML")
        return
    amount = int(message.text)
    if amount < 100:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="profile"), InlineKeyboardButton(text="❌ Закрыть", callback_data="close_notify")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        await message.edit_text("❗️ <b>Минимальная сумма для вывода — 100 ₽</b>", reply_markup=kb, parse_mode="HTML")
        return
    if amount > user.balance:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="profile"), InlineKeyboardButton(text="❌ Закрыть", callback_data="close_notify")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        await message.edit_text("❗️ <b>Недостаточно средств на балансе!</b>", reply_markup=kb, parse_mode="HTML")
        return
    await state.update_data(amount=amount)
    await message.edit_text("💳 <b>Введите реквизиты для вывода (номер карты, телефон и т.д.):</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]]), parse_mode="HTML")
    await state.set_state(WithdrawFSM.requisites)

@router.message(WithdrawFSM.requisites)
async def withdraw_requisites(message: Message, state: FSMContext):
    await state.update_data(requisites=message.text)
    data = await state.get_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="profile"), InlineKeyboardButton(text="❌ Закрыть", callback_data="close_notify")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    await message.edit_text(f"<b>💸 Подтвердите заявку на вывод:</b>\nСумма: <b>{data['amount']}</b> ₽\nРеквизиты: <b>{data['requisites']}</b>\n\nОтправить заявку? (да/нет)", parse_mode="HTML", reply_markup=kb)
    await state.set_state(WithdrawFSM.confirm)

@router.message(WithdrawFSM.confirm)
async def withdraw_confirm(message: Message, state: FSMContext):
    if message.text.lower() not in ["да", "yes", "+"]:
        await message.edit_text("❌ <b>Заявка отменена.</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]]), parse_mode="HTML")
        await state.clear()
        return
    data = await state.get_data()
    user = await get_or_create_user(message.from_user.id)
    async with async_session() as session:
        hist = BalanceHistory(user_id=user.id, change=-int(data['amount']), type="вывод", comment=data['requisites'], created_at=datetime.utcnow())
        user.balance -= int(data['amount'])
        session.add(hist)
        await session.merge(user)
        await session.commit()
    await message.edit_text("✅ <b>Заявка на вывод отправлена!</b>\nПожалуйста, ожидайте подтверждения от администратора. 🕓", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]]))
    await state.clear()
    # Уведомление админов
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_withdraw_{user.tg_id}_{data['amount']}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_withdraw_{user.tg_id}_{data['amount']}")]
    ])
    for admin_id in settings.ADMIN_IDS:
        try:
            await message.bot.send_message(
                admin_id,
                f"<b>Новая заявка на вывод!</b>\nПользователь: <code>{user.fio or user.tg_id}</code>\nID: <code>{user.tg_id}</code>\nСумма: <b>{data['amount']} ₽</b>\nРеквизиты: <b>{data['requisites']}</b>",
                reply_markup=kb,
                parse_mode="HTML"
            )
        except Exception:
            pass

@router.callback_query(F.data == "balance_history")
async def show_balance_history(call: CallbackQuery):
    user = await get_or_create_user(call.from_user.id)
    async with async_session() as session:
        result = await session.execute(
            BalanceHistory.__table__.select().where(BalanceHistory.user_id == user.id).order_by(BalanceHistory.created_at.desc()).limit(10)
        )
        history = result.fetchall()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="profile"), InlineKeyboardButton(text="❌ Закрыть", callback_data="close_notify")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    if not history:
        try:
            await call.message.edit_text("<b>📊 История баланса пуста.</b>", reply_markup=kb, parse_mode="HTML")
        except Exception:
            await call.message.answer("<b>📊 История баланса пуста.</b>", reply_markup=kb, parse_mode="HTML")
        await call.answer()
        return
    text = "<b>📊 Последние операции:</b>\n"
    for row in history:
        msk_time = row.created_at + timedelta(hours=3)
        emoji = "➕" if row.change > 0 else "➖"
        text += f"{msk_time.strftime('%d.%m %H:%M')} (МСК) | {row.type} | {emoji} {abs(row.change)} ₽ | {row.comment or ''}\n"
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await call.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()

@router.callback_query(F.data == "my_withdraw_requests")
async def show_my_withdraw_requests(call: CallbackQuery):
    user = await get_or_create_user(call.from_user.id)
    from models.user import BalanceHistory
    from sqlalchemy import select, desc
    async with async_session() as session:
        result = await session.execute(
            select(BalanceHistory)
            .where(BalanceHistory.user_id == user.id, BalanceHistory.type == "вывод")
            .order_by(desc(BalanceHistory.created_at))
        )
        history = result.scalars().all()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="profile"), InlineKeyboardButton(text="❌ Закрыть", callback_data="close_notify")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    if not history:
        try:
            await call.message.edit_text("<b>У вас нет заявок на вывод.</b> 🕓", parse_mode="HTML", reply_markup=kb)
        except Exception:
            await call.message.answer("<b>У вас нет заявок на вывод.</b> 🕓", parse_mode="HTML", reply_markup=kb)
        await call.answer()
        return
    text = "<b>Ваши заявки на вывод:</b>\n"
    for row in history:
        # Определяем статус заявки
        status = "🕓 В процессе"
        # Проверяем отмену
        cancel = False
        async with async_session() as session2:
            cancel_result = await session2.execute(
                select(BalanceHistory)
                .where(BalanceHistory.user_id == row.user_id, BalanceHistory.type == "отмена вывода", BalanceHistory.change == abs(row.change))
            )
            cancel_hist = cancel_result.scalar_one_or_none()
            if cancel_hist:
                status = "❌ Отклонена"
                cancel = True
        if not cancel:
            # Если заявка была одобрена (по логике — если change < 0 и нет отмены, значит одобрена вручную)
            # Но в текущей реализации нет явного признака, поэтому оставляем "В процессе" до ручного удаления
            pass
        msk_time = row.created_at + timedelta(hours=3)
        text += f"<b>{abs(row.change)} ₽</b> | {row.comment or ''} | {msk_time.strftime('%d.%m %H:%M')} (МСК) | <b>{status}</b>\n"
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await call.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()

@router.callback_query(F.data == "close_notify")
async def close_notify(call: CallbackQuery):
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.answer()


@router.callback_query(F.data == "main_menu")
async def main_menu_cb(call: CallbackQuery):
    try:
        await call.message.edit_text("Главное меню:", reply_markup=user_main_menu())
    except Exception:
        await call.message.answer("Главное меню:", reply_markup=user_main_menu())
    await call.answer()
