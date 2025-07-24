from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.future import select
from core.db import async_session
from models.user import User
from services.user_service import update_user_status
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from datetime import datetime, timedelta
from utils.misc import log_admin_action

router = Router()

@router.callback_query(F.data == "users")
async def open_users(call: CallbackQuery):
    await call.answer()
    await show_users(call.message)

@router.message(F.text == "Список пользователей")
async def show_users(message: Message):
    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{u.fio or u.tg_id}", callback_data=f"user_{u.tg_id}")] for u in users
        ] + [[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu"), InlineKeyboardButton(text="❌ Закрыть", callback_data="close_notify")]])
        if not users:
            try:
                await message.edit_text("Пользователей нет.", reply_markup=kb)
            except Exception:
                await message.answer("Пользователей нет.", reply_markup=kb)
            return
        try:
            await message.edit_text("Список пользователей:", reply_markup=kb)
        except Exception:
            await message.answer("Список пользователей:", reply_markup=kb)

@router.callback_query(F.data.startswith("user_"))
async def user_info(call: CallbackQuery):
    tg_id = int(call.data.split("_")[1])
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if not user:
            await call.answer("Пользователь не найден", show_alert=True)
            return
        text = f"<b>ФИО:</b> {user.fio}\n<b>Возраст:</b> {user.age}\n<b>ID:</b> {user.tg_id}\n<b>Баланс:</b> {user.balance} ₽\nСтатус: {'Заблокирован' if user.is_blocked else 'Активен'}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Пополнить", callback_data=f"balance_add_{user.tg_id}"),
             InlineKeyboardButton(text="➖ Штраф", callback_data=f"balance_fine_{user.tg_id}")],
            [InlineKeyboardButton(text="⚙️ Корректировка", callback_data=f"balance_corr_{user.tg_id}")],
            [InlineKeyboardButton(text="🚫 Заблокировать навсегда", callback_data=f"block_forever_{user.tg_id}")],
            [InlineKeyboardButton(text="⏳ Заблокировать на 1 день", callback_data=f"block_1d_{user.tg_id}")],
            [InlineKeyboardButton(text="🔓 Разблокировать", callback_data=f"unblock_{user.tg_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="users"), InlineKeyboardButton(text="❌ Закрыть", callback_data="close_notify")]
        ])
        if user.passport_photo:
            try:
                await call.message.delete()
            except Exception:
                pass
            await call.message.answer_photo(user.passport_photo, caption=text, reply_markup=kb, parse_mode="HTML")
        else:
            try:
                await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                await call.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await call.answer()

@router.callback_query(F.data.startswith("block_forever_"))
async def block_forever(call: CallbackQuery):
    tg_id = int(call.data.split("_")[2])
    await update_user_status(tg_id, is_blocked=True)
    # Логируем действие
    from models.user import AdminActionLog
    async with async_session() as session:
        log = AdminActionLog(admin_id=call.from_user.id, user_id=tg_id, action="block_forever", comment=None)
        session.add(log)
        await session.commit()
    await call.answer("Пользователь заблокирован навсегда", show_alert=True)
    await call.message.edit_text("Пользователь заблокирован навсегда.")

@router.callback_query(F.data.startswith("block_1d_"))
async def block_1d(call: CallbackQuery):
    tg_id = int(call.data.split("_")[2])
    from datetime import datetime, timedelta
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_blocked = True
            user.comment = f"unblock_at:{(datetime.utcnow() + timedelta(days=1)).isoformat()}"
            await session.merge(user)
            # Логируем действие
            from models.user import AdminActionLog
            log = AdminActionLog(admin_id=call.from_user.id, user_id=tg_id, action="block_1d", comment=user.comment)
            session.add(log)
            await session.commit()
    await call.answer("Пользователь заблокирован на 1 день", show_alert=True)
    await call.message.edit_text("Пользователь заблокирован на 1 день.")

@router.callback_query(F.data.startswith("unblock_"))
async def unblock_user(call: CallbackQuery):
    tg_id = int(call.data.split("_")[1])
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_blocked = False
            user.comment = None
            await session.merge(user)
            # Логируем действие
            from models.user import AdminActionLog
            log = AdminActionLog(admin_id=call.from_user.id, user_id=tg_id, action="unblock", comment=None)
            session.add(log)
            await session.commit()
            # Уведомляем пользователя о разблокировке
            try:
                await call.bot.send_message(tg_id, "Ваша блокировка снята. Вы снова можете пользоваться ботом! 🎉")
            except Exception:
                pass
    await call.answer("Пользователь разблокирован", show_alert=True)
    await call.message.edit_text("Пользователь разблокирован.")

@router.callback_query(F.data.startswith("refs_"))
async def show_refs(call: CallbackQuery):
    tg_id = int(call.data.split("_")[1])
    async with async_session() as session:
        result = await session.execute(select(Referral).where(Referral.inviter_id == tg_id))
        refs = result.scalars().all()
        if not refs:
            await call.answer("Нет рефералов", show_alert=True)
            return
        text = "Рефералы пользователя:\n"
        for ref in refs:
            user_result = await session.execute(select(User).where(User.tg_id == ref.invited_id))
            invited = user_result.scalar_one_or_none()
            if invited:
                text += f"- {invited.fio or invited.tg_id} (ID: {invited.tg_id})\n"
        await call.message.edit_text(text)

class BalanceChange(StatesGroup):
    action = State()
    amount = State()
    comment = State()
    user_id = State()

@router.callback_query(F.data.regexp(r"^balance_(add|fine|corr)_\d+"))
async def start_balance_change(call: CallbackQuery, state: FSMContext):
    _, action, user_id = call.data.split('_', 2)
    log_admin_action(call.from_user.id, f"balance_{action}", f"target_user_id={user_id}")
    await state.set_state(BalanceChange.amount)
    await state.update_data(action=action, user_id=user_id)
    if action == "add":
        await call.message.answer("Введите сумму для пополнения баланса:")
    elif action == "fine":
        await call.message.answer("Введите сумму штрафа (будет вычтено):")
    elif action == "corr":
        await call.message.answer("Введите сумму корректировки (может быть + или -):")
    await call.answer()

@router.message(StateFilter(BalanceChange.amount))
async def balance_amount_entered(message: Message, state: FSMContext):
    data = await state.get_data()
    if not message.text.lstrip('-').isdigit():
        await message.answer("Введите корректную сумму (целое число):")
        return
    await state.update_data(amount=int(message.text))
    await message.answer("Введите комментарий к операции (или '-' если не нужен):")
    await state.set_state(BalanceChange.comment)

@router.message(StateFilter(BalanceChange.comment))
async def balance_comment_entered(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = int(data["user_id"])
    amount = int(data["amount"])
    comment = message.text if message.text != '-' else ''
    from core.db import async_session
    from models.user import User
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("Пользователь не найден.")
            await state.clear()
            return
        if data["action"] == "add":
            user.balance += abs(amount)
            op = "пополнение"
        elif data["action"] == "fine":
            user.balance -= abs(amount)
            op = "штраф"
        elif data["action"] == "corr":
            user.balance += amount
            op = "корректировка"
        await session.commit()
    await message.answer(f"Баланс пользователя изменён!\nОперация: <b>{op}</b>\nСумма: <b>{amount}</b>\nКомментарий: {comment}", parse_mode="HTML")
    # Можно уведомить пользователя
    try:
        from aiogram import Bot
        bot: Bot = message.bot
        await bot.send_message(user_id, f"❗️Ваш баланс изменён. Операция: <b>{op}</b>\nСумма: <b>{amount}</b>\nКомментарий: {comment}", parse_mode="HTML")
    except Exception:
        pass
    await state.clear() 

@router.callback_query(F.data.regexp(r"^approve_withdraw_\d+_\d+"))
async def approve_withdraw(call: CallbackQuery):
    _, _, user_id, amount = call.data.split('_')
    user_id = int(user_id)
    amount = int(amount)
    log_admin_action(call.from_user.id, "approve_withdraw", f"user_id={user_id}, amount={amount}")
    # Обновляем статус заявки и баланс (если нужно)
    from core.db import async_session
    from models.user import User, BalanceHistory
    from datetime import datetime
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            # Здесь можно добавить запись в историю, если нужно явно фиксировать выплату
            hist = BalanceHistory(user_id=user.id, change=0, type="выплата", comment="Заявка одобрена админом", created_at=datetime.utcnow())
            session.add(hist)
            await session.merge(user)
            await session.commit()
    # Уведомляем пользователя
    try:
        await call.bot.send_message(user_id, f"✅ Ваша заявка на вывод <b>{amount} ₽</b> одобрена! Ожидайте поступления средств на указанные реквизиты. 🕓", parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка отправки сообщения о принятии заявки на вывод пользователю {user_id}: {e}")
    await call.message.edit_text("Заявка одобрена и пользователь уведомлён.")
    await call.answer()

@router.callback_query(F.data.regexp(r"^reject_withdraw_\d+_\d+"))
async def reject_withdraw(call: CallbackQuery):
    _, _, user_id, amount = call.data.split('_')
    user_id = int(user_id)
    amount = int(amount)
    log_admin_action(call.from_user.id, "reject_withdraw", f"user_id={user_id}, amount={amount}")
    # Возвращаем деньги пользователю
    from core.db import async_session
    from models.user import User, BalanceHistory
    from datetime import datetime
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.balance += amount
            hist = BalanceHistory(user_id=user.id, change=amount, type="отмена вывода", comment="Заявка отклонена админом", created_at=datetime.utcnow())
            session.add(hist)
            await session.merge(user)
            await session.commit()
    # Уведомляем пользователя
    try:
        await call.bot.send_message(user_id, f"❌ Ваша заявка на вывод <b>{amount} ₽</b> отклонена. Средства возвращены на баланс.", parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка отправки сообщения об отклонении заявки на вывод пользователю {user_id}: {e}")
    await call.message.edit_text("Заявка отклонена, средства возвращены.")
    await call.answer()

@router.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    from core.db import async_session
    from models.user import User, BalanceHistory
    from models.job import Job
    from sqlalchemy import select, func, desc
    from datetime import datetime, timedelta
    async with async_session() as session:
        users_count = (await session.execute(select(func.count()).select_from(User))).scalar()
        jobs_count = (await session.execute(select(func.count()).select_from(Job))).scalar()
        active_jobs = (await session.execute(select(func.count()).select_from(Job).where(Job.end_time > datetime.utcnow()))).scalar()
        payouts = (await session.execute(BalanceHistory.__table__.select().where(BalanceHistory.type == "вывод"))).fetchall()
        total_payout = sum(abs(row.change) for row in payouts)
        # Топ-5 пользователей по балансу
        top_balance = (await session.execute(select(User).order_by(desc(User.balance)).limit(5))).scalars().all()
        # Топ-5 по количеству выполненных заданий (по истории баланса type='выплата')
        top_jobs = (await session.execute(
            select(User, func.count(BalanceHistory.id).label('cnt'))
            .join(BalanceHistory, BalanceHistory.user_id == User.id)
            .where(BalanceHistory.type == 'выплата')
            .group_by(User.id)
            .order_by(desc('cnt'))
            .limit(5)
        )).all()
        # Количество заявок на вывод за месяц
        month_ago = datetime.utcnow() - timedelta(days=30)
        withdraws_month = (await session.execute(
            select(func.count()).select_from(BalanceHistory)
            .where(BalanceHistory.type == 'вывод', BalanceHistory.created_at > month_ago)
        )).scalar()
    text = (f"<b>📊 Статистика</b>\n"
            f"Пользователей: <b>{users_count}</b>\n"
            f"Заданий всего: <b>{jobs_count}</b>\n"
            f"Активных заданий: <b>{active_jobs}</b>\n"
            f"Выплачено всего: <b>{total_payout} ₽</b>\n"
            f"Заявок на вывод за месяц: <b>{withdraws_month}</b>\n\n"
            f"<b>🏆 Топ-5 по балансу:</b>\n" +
            ''.join([f"{i+1}. {u.fio or u.tg_id}: <b>{u.balance} ₽</b>\n" for i, u in enumerate(top_balance)]) +
            f"\n<b>🏅 Топ-5 по выполненным заданиям:</b>\n" +
            ''.join([f"{i+1}. {u.fio or u.tg_id}: <b>{cnt}</b>\n" for i, (u, cnt) in enumerate(top_jobs)])
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close_notify")]
    ])
    await call.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "close_notify")
async def close_notify(call: CallbackQuery):
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.answer() 

class NewsFSM(StatesGroup):
    text = State()
    confirm = State()

@router.callback_query(F.data == "admin_news")
async def start_news(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Введите текст новости для рассылки:")
    await state.set_state(NewsFSM.text)
    await call.answer()

@router.message(NewsFSM.text)
async def news_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer(f"<b>Текст рассылки:</b>\n{message.text}\n\nОтправить всем пользователям? (да/нет)", parse_mode="HTML")
    await state.set_state(NewsFSM.confirm)

@router.message(NewsFSM.confirm)
async def news_confirm(message: Message, state: FSMContext):
    if message.text.lower() not in ["да", "yes", "+"]:
        await message.answer("Рассылка отменена.")
        await state.clear()
        return
    data = await state.get_data()
    from core.db import async_session
    from models.user import User
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    async with async_session() as session:
        result = await session.execute(User.__table__.select().where(User.is_blocked == False, User.is_approved == True))
        users = result.fetchall()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close_notify")]
    ])
    count = 0
    for row in users:
        try:
            await message.bot.send_message(row.tg_id, data['text'], reply_markup=kb)
            count += 1
        except Exception:
            pass
    await message.answer(f"Рассылка отправлена <b>{count}</b> пользователям.", parse_mode="HTML")
    await state.clear() 
    log_admin_action(message.from_user.id, "news_broadcast", f"text={data['text']}")

@router.callback_query(F.data == "admin_menu")
async def admin_menu_cb(call: CallbackQuery):
    from keyboards.admin import admin_main_menu
    await call.message.answer("Админ-меню:", reply_markup=admin_main_menu())
    await call.answer() 

@router.callback_query(F.data == "withdraw_requests")
async def show_withdraw_requests(call: CallbackQuery):
    from models.user import BalanceHistory, User
    from sqlalchemy import select, desc
    async with async_session() as session:
        result = await session.execute(
            select(BalanceHistory, User)
            .join(User, User.id == BalanceHistory.user_id)
            .where(BalanceHistory.type == "вывод")
            .order_by(desc(BalanceHistory.created_at))
        )
        rows = result.fetchall()
    if not rows:
        await call.message.answer("<b>Заявок на вывод нет.</b> 🕓", parse_mode="HTML")
        await call.answer()
        return
    # Кнопки для каждой заявки
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{user.fio or user.tg_id} | {abs(hist.change)}₽ | {(hist.created_at + timedelta(hours=3)).strftime('%d.%m %H:%M')} (МСК)", callback_data=f"withdraw_info_{hist.id}")]
        for hist, user in rows
    ])
    await call.message.answer("<b>Заявки на вывод:</b>", reply_markup=kb, parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.regexp(r"^withdraw_info_\d+"))
async def show_withdraw_info(call: CallbackQuery):
    hist_id = int(call.data.split('_')[-1])
    from models.user import BalanceHistory, User
    from sqlalchemy import select
    async with async_session() as session:
        result = await session.execute(
            select(BalanceHistory, User)
            .join(User, User.id == BalanceHistory.user_id)
            .where(BalanceHistory.id == hist_id)
        )
        row = result.first()
    if not row:
        await call.message.answer("Заявка не найдена.")
        await call.answer()
        return
    hist, user = row
    msk_time = hist.created_at + timedelta(hours=3)
    text = (f"<b>Заявка на вывод</b>\n"
            f"Пользователь: <b>{user.fio or user.tg_id}</b>\n"
            f"ID: <code>{user.tg_id}</code>\n"
            f"Сумма: <b>{abs(hist.change)} ₽</b>\n"
            f"Реквизиты: <b>{hist.comment or '-'} </b>\n"
            f"Дата: <b>{msk_time.strftime('%d.%m %H:%M')} (МСК)</b>")
    await call.message.answer(text, parse_mode="HTML")
    await call.answer() 

@router.callback_query(F.data == "admin_bulk")
async def admin_bulk(call: CallbackQuery, state: FSMContext):
    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
    data = await state.get_data()
    selected = data.get("bulk_selected", [])
    buttons = []
    row = []
    for i, u in enumerate(users):
        checked = " ✅" if u.tg_id in selected else ""
        row.append(InlineKeyboardButton(text=f"{u.fio or u.tg_id}{' 🔒' if u.is_blocked else ''}{checked}", callback_data=f"bulkselect_{u.tg_id}"))
        if (i+1) % 3 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="✅ Продолжить", callback_data="bulk_continue"), InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu"), InlineKeyboardButton(text="❌ Закрыть", callback_data="close_notify")])
    await state.update_data(bulk_selected=selected)
    try:
        await call.message.edit_text("Выберите пользователей для массового действия:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await call.message.answer("Выберите пользователей для массового действия:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await call.answer()

@router.callback_query(F.data.startswith("bulkselect_"))
async def bulk_select(call: CallbackQuery, state: FSMContext):
    tg_id = int(call.data.split("_")[1])
    data = await state.get_data()
    selected = data.get("bulk_selected", [])
    if tg_id in selected:
        selected.remove(tg_id)
    else:
        selected.append(tg_id)
    await state.update_data(bulk_selected=selected)
    await call.answer(f"Выбрано: {len(selected)}")

class BulkMailFSM(StatesGroup):
    text = State()

@router.callback_query(F.data == "bulk_continue")
async def bulk_continue(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("bulk_selected", [])
    if not selected:
        await call.answer("Не выбрано ни одного пользователя", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Заблокировать", callback_data="bulk_block")],
        [InlineKeyboardButton(text="🔓 Разблокировать", callback_data="bulk_unblock")],
        [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="bulk_mail")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu")]
    ])
    await call.message.answer(f"Выбрано пользователей: {len(selected)}. Какое действие выполнить?", reply_markup=kb)
    await call.answer()

@router.callback_query(F.data == "bulk_mail")
async def bulk_mail(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Введите текст рассылки:")
    await state.set_state(BulkMailFSM.text)
    await call.answer()

@router.message(BulkMailFSM.text)
async def bulk_mail_text(message: Message, state: FSMContext):
    data = await state.get_data()
    selected = data.get("bulk_selected", [])
    text = message.text
    count = 0
    for tg_id in selected:
        try:
            await message.bot.send_message(tg_id, text)
            count += 1
        except Exception:
            pass
    await message.answer(f"Рассылка отправлена <b>{count}</b> пользователям.", parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data == "bulk_block")
async def bulk_block(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("bulk_selected", [])
    from models.user import AdminActionLog
    async with async_session() as session:
        for tg_id in selected:
            result = await session.execute(select(User).where(User.tg_id == tg_id))
            user = result.scalar_one_or_none()
            if user:
                user.is_blocked = True
                session.add(AdminActionLog(admin_id=call.from_user.id, user_id=tg_id, action="bulk_block", comment=None))
        await session.commit()
    await call.message.answer(f"Заблокировано пользователей: {len(selected)}")
    await call.answer()

@router.callback_query(F.data == "bulk_unblock")
async def bulk_unblock(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("bulk_selected", [])
    from models.user import AdminActionLog
    async with async_session() as session:
        for tg_id in selected:
            result = await session.execute(select(User).where(User.tg_id == tg_id))
            user = result.scalar_one_or_none()
            if user:
                user.is_blocked = False
                user.comment = None
                session.add(AdminActionLog(admin_id=call.from_user.id, user_id=tg_id, action="bulk_unblock", comment=None))
        await session.commit()
    await call.message.answer(f"Разблокировано пользователей: {len(selected)}")
    await call.answer() 