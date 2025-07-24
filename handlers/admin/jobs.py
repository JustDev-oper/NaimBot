from aiogram import Router, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InputMediaPhoto, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from services.job_service import create_job, get_jobs, get_job
from services.user_service import get_or_create_user
from core.config import settings
from keyboards.admin import job_list_keyboard, job_users_keyboard, admin_main_menu
from datetime import datetime
from aiogram.filters import StateFilter
import calendar

router = Router()

RU_MONTHS = [
    '', 'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
]

class JobCreate(StatesGroup):
    title = State()
    description = State()
    pay = State()
    start_time = State()
    end_time = State()
    min_age = State()
    max_age = State()
    address = State()
    workers_needed = State()
    photo = State()

CANCEL_INLINE_KB = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_job_create")]])

@router.callback_query(F.data == "create_job")
async def open_create_job(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await start_job_create(call.message, state)

@router.callback_query(F.data == "job_list")
async def show_job_list(call: CallbackQuery):
    jobs = await get_jobs()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu")]
    ])
    if not jobs:
        try:
            await call.message.edit_text("<b>📜 Нет созданных заданий.</b> 🗒", reply_markup=kb, parse_mode="HTML")
        except Exception:
            await call.message.answer("<b>📜 Нет созданных заданий.</b> 🗒", reply_markup=kb, parse_mode="HTML")
        await call.answer()
        return
    try:
        await call.message.edit_text("<b>📋 Список заданий:</b> 📋", reply_markup=job_list_keyboard(jobs), parse_mode="HTML")
    except Exception:
        await call.message.answer("<b>📋 Список заданий:</b> 📋", reply_markup=job_list_keyboard(jobs), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.regexp(r"^job_\d+"))
async def show_job_users(call: CallbackQuery):
    job_id = int(call.data.split('_')[1])
    job = await get_job(job_id)
    if not job:
        try:
            await call.message.edit_text("<b>❌ Задание не найдено!</b> 🔍", reply_markup=admin_main_menu(), parse_mode="HTML")
        except Exception:
            await call.message.answer("<b>❌ Задание не найдено!</b> 🔍", reply_markup=admin_main_menu(), parse_mode="HTML")
        await call.answer()
        return
    users = []
    if job.workers:
        for uid in job.workers.split(','):
            if uid:
                user = await get_or_create_user(int(uid))
                users.append(user)
    text = f"<b>📝 Задание:</b> <b>{job.title}</b>\n<b>📝 Описание:</b> {job.description}\n<b>💰 Оплата:</b> {job.pay} ₽\n<b>👥 Работников нужно:</b> {job.workers_needed}\n<b>✅ Записано:</b> {len(users)}"
    if users:
        text += "\n\n<b>🙋‍♂️ Записанные пользователи:</b>"
    else:
        text += "\n\n<b>❌ Нет записанных пользователей.</b>"
    try:
        await call.message.edit_text(text, reply_markup=job_users_keyboard(job.id, users), parse_mode="HTML")
    except Exception:
        await call.message.answer(text, reply_markup=job_users_keyboard(job.id, users), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.regexp(r"^remove_\d+_\d+"))
async def remove_user_from_job(call: CallbackQuery, bot):
    _, job_id, user_id = call.data.split('_')
    job = await get_job(int(job_id))
    if not job:
        try:
            await call.message.edit_text("<b>❌ Задание не найдено!</b> 🔍", reply_markup=admin_main_menu(), parse_mode="HTML")
        except Exception:
            await call.message.answer("<b>❌ Задание не найдено!</b> 🔍", reply_markup=admin_main_menu(), parse_mode="HTML")
        await call.answer()
        return
    # Удаляем пользователя из списка
    ids = [uid for uid in job.workers.split(',') if uid and uid != user_id]
    job.workers = ','.join(ids)
    from core.db import async_session
    async with async_session() as session:
        await session.merge(job)
        await session.commit()
    # Уведомляем пользователя
    try:
        await bot.send_message(int(user_id), f"❗️Вы были сняты с задания <b>{job.title}</b> по просьбе или решению администрации.")
    except Exception:
        pass
    try:
        await call.message.edit_text(f"🙍‍♂️ Пользователь <b>{user_id}</b> снят с задания!", reply_markup=job_users_keyboard(job.id, [await get_or_create_user(int(uid)) for uid in ids]), parse_mode="HTML")
    except Exception:
        await call.message.answer(f"🙍‍♂️ Пользователь <b>{user_id}</b> снят с задания!", reply_markup=job_users_keyboard(job.id, [await get_or_create_user(int(uid)) for uid in ids]), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "job_history")
async def show_job_history(call: CallbackQuery):
    jobs = await get_jobs()  # Можно добавить фильтр по завершённым, если появится статус
    if not jobs:
        try:
            await call.message.edit_text("<b>📜 История заданий пуста.</b> 🗒", reply_markup=admin_main_menu(), parse_mode="HTML")
        except Exception:
            await call.message.answer("<b>📜 История заданий пуста.</b> 🗒", reply_markup=admin_main_menu(), parse_mode="HTML")
        await call.answer()
        return
    for job in jobs:
        users = []
        if job.workers:
            for uid in job.workers.split(','):
                if uid:
                    user = await get_or_create_user(int(uid))
                    users.append(user)
        text = f"<b>📝 Задание:</b> <b>{job.title}</b>\n<b>📝 Описание:</b> {job.description}\n<b>📍 Адрес:</b> {getattr(job, 'address', '—')}\n<b>💸 Оплата:</b> {job.pay} ₽\n<b>👥 Работников нужно:</b> {job.workers_needed}\n<b>✅ Записано:</b> {len(users)}"
        if users:
            text += "\n\n<b>🙋‍♂️ Участвовали:</b>"
        else:
            text += "\n\n<b>❌ Нет участников.</b>"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🙍‍♂️ {u.fio or u.tg_id}", callback_data=f"profile_{u.tg_id}")] for u in users
        ])
        try:
            await call.message.edit_text(text, reply_markup=kb if users else admin_main_menu(), parse_mode="HTML")
        except Exception:
            await call.message.answer(text, reply_markup=kb if users else admin_main_menu(), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.regexp(r"^profile_\d+"))
async def show_user_profile_from_job(call: CallbackQuery):
    tg_id = int(call.data.split('_')[1])
    user = await get_or_create_user(tg_id)
    text = f"<b>Профиль пользователя</b>\n<b>ФИО:</b> {user.fio}\n<b>Возраст:</b> {user.age}\n<b>ID:</b> {user.tg_id}"
    await call.message.answer(text)
    await call.answer()

@router.callback_query(F.data == "cancel_job_create")
async def cancel_job_create_cb(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Создание задания отменено.", reply_markup=admin_main_menu(), parse_mode="HTML")
    await call.answer()

@router.message(F.text == "Создать задание")
async def start_job_create(message: Message, state: FSMContext):
    await message.answer("Введите название задания:", reply_markup=CANCEL_INLINE_KB)
    await state.set_state(JobCreate.title)

@router.message(JobCreate.title)
async def job_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите описание задания:", reply_markup=CANCEL_INLINE_KB)
    await state.set_state(JobCreate.description)

@router.message(JobCreate.description)
async def job_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Введите оплату за смену (число):", reply_markup=CANCEL_INLINE_KB)
    await state.set_state(JobCreate.pay)

@router.message(JobCreate.pay)
async def job_pay(message: Message, state: FSMContext):
    await state.update_data(pay=int(message.text))
    await message.answer("Введите <b>число, время начала и время конца</b> через пробел. Пример: <b>28 15:00 16:00</b>", parse_mode="HTML", reply_markup=CANCEL_INLINE_KB)
    await state.set_state(JobCreate.start_time)

@router.message(JobCreate.start_time)
async def job_start_time(message: Message, state: FSMContext):
    try:
        parts = message.text.strip().split()
        if len(parts) != 3:
            raise ValueError
        day = int(parts[0])
        start_time = parts[1]
        end_time = parts[2]
        now = datetime.now()
        month = now.month
        year = now.year
        start_dt = datetime.strptime(f"{day}.{month}.{year} {start_time}", "%d.%m.%Y %H:%M")
        end_dt = datetime.strptime(f"{day}.{month}.{year} {end_time}", "%d.%m.%Y %H:%M")
        await state.update_data(start_time=start_dt.strftime('%Y-%m-%d %H:%M'))
        await state.update_data(end_time=end_dt.strftime('%Y-%m-%d %H:%M'))
        await message.answer("Минимальный возраст?", reply_markup=CANCEL_INLINE_KB)
        await state.set_state(JobCreate.min_age)
    except Exception:
        await message.answer("Введите дату и время в формате: <b>28 15:00 16:00</b> (число, время начала, время конца)", parse_mode="HTML", reply_markup=CANCEL_INLINE_KB)

@router.message(JobCreate.min_age)
async def job_min_age(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) < 16:
        await message.answer("Введите минимальный возраст числом (от 16):", reply_markup=CANCEL_INLINE_KB)
        return
    await state.update_data(min_age=int(message.text))
    await message.answer("Укажите максимальный возраст для задания (или '-' если не ограничено):", reply_markup=CANCEL_INLINE_KB)
    await state.set_state(JobCreate.max_age)

@router.message(JobCreate.max_age)
async def job_max_age(message: Message, state: FSMContext):
    if message.text == '-' or message.text == "0":
        await state.update_data(max_age=99)
    elif not message.text.isdigit() or int(message.text) < 16:
        await message.answer("Введите максимальный возраст числом (от 16) или '-' если не ограничено:", reply_markup=CANCEL_INLINE_KB)
        return
    else:
        await state.update_data(max_age=int(message.text))
    await message.answer("Введите адрес задания:", reply_markup=CANCEL_INLINE_KB)
    await state.set_state(JobCreate.address)

@router.message(JobCreate.address)
async def job_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer("Сколько нужно работников?", reply_markup=CANCEL_INLINE_KB)
    await state.set_state(JobCreate.workers_needed)

@router.message(JobCreate.workers_needed)
async def job_workers(message: Message, state: FSMContext):
    await state.update_data(workers_needed=int(message.text))
    await message.answer("Пришлите фото (или напишите 'нет'):", reply_markup=CANCEL_INLINE_KB)
    await state.set_state(JobCreate.photo)

@router.message(JobCreate.photo, F.photo)
async def job_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await finish_job_create(message, state, photo_id)

@router.message(JobCreate.photo)
async def job_no_photo(message: Message, state: FSMContext):
    if message.text.lower() == 'нет':
        await finish_job_create(message, state, None)
    else:
        await message.answer("Пришлите фото или напишите 'нет'", reply_markup=CANCEL_INLINE_KB)

async def finish_job_create(message: Message, state: FSMContext, photo_id):
    data = await state.get_data()
    job = await create_job(
        title=data['title'],
        description=data['description'],
        pay=data['pay'],
        start_time=datetime.strptime(data['start_time'], '%Y-%m-%d %H:%M'),
        end_time=datetime.strptime(data['end_time'], '%Y-%m-%d %H:%M'),
        min_age=data['min_age'],
        max_age=data['max_age'],
        address=data['address'],
        photo=photo_id,
        workers_needed=data['workers_needed']
    )
    from core.config import settings
    group_message_id = None
    if settings.WORKERS_CHAT_ID:
        total = job.workers_needed
        # Форматируем дату и время
        day = job.start_time.day
        month = RU_MONTHS[job.start_time.month]
        start_time_str = job.start_time.strftime('%H:%M')
        end_time_str = job.end_time.strftime('%H:%M')
        date_str = f"{day} {month} {start_time_str} - {end_time_str}"
        text = (f"<b>📝 Новое задание!</b>\n"
                f"<b>Название:</b> {job.title}\n"
                f"<b>Описание:</b> {job.description}\n"
                f"<b>Адрес:</b> {job.address}\n"
                f"<b>Оплата:</b> {job.pay} ₽\n"
                f"<b>Возраст:</b> {job.min_age} - {job.max_age if job.max_age != 99 else 'без ограничений'}\n"
                f"<b>Время:</b> {date_str}\n"
                f"<b>Мест:</b> {total}")
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        # Кнопка-ссылка на бота с параметром job_id
        bot_username = settings.BOT_USERNAME  # всегда без @
        deep_link = f"https://t.me/{bot_username}?start=job_{job.id}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✋ Записаться", url=deep_link)]
        ])
        bot = message.bot
        try:
            if photo_id:
                sent = await bot.send_photo(settings.WORKERS_CHAT_ID, photo_id, caption=text, reply_markup=kb, parse_mode="HTML")
                group_message_id = sent.message_id
            else:
                sent = await bot.send_message(settings.WORKERS_CHAT_ID, text, reply_markup=kb, parse_mode="HTML")
                group_message_id = sent.message_id
        except Exception as e:
            print(f"Ошибка отправки сообщения в чат: {e}")
    # Сохраняем message_id в Job
    if group_message_id:
        from core.db import async_session
        async with async_session() as session:
            job.group_message_id = group_message_id
            await session.merge(job)
            await session.commit()
    # Рассылка подписанным пользователям
    from core.db import async_session
    from models.user import User
    async with async_session() as session:
        result = await session.execute(User.__table__.select().where(User.is_subscribed == True, User.is_blocked == False, User.is_approved == True))
        users = result.fetchall()
    for row in users:
        try:
            await message.bot.send_message(row.tg_id, f"<b>Новое задание!</b>\n{job.title}\n{job.description}", parse_mode="HTML")
        except Exception as e:
            print(f"Ошибка отправки пользователю {row.tg_id}: {e}")
    await message.answer("Задание создано!", reply_markup=admin_main_menu(), parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data.regexp(r"^delete_job_\d+"))
async def confirm_delete_job(call: CallbackQuery):
    job_id = int(call.data.split('_')[-1])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❗️ Подтвердить удаление", callback_data=f"delete_job_confirm_{job_id}")],
        [InlineKeyboardButton(text="Отмена", callback_data=f"job_{job_id}")]
    ])
    try:
        await call.message.edit_text("Вы уверены, что хотите удалить это задание? Это действие <b>необратимо</b>!", reply_markup=kb, parse_mode="HTML")
    except Exception:
        await call.message.answer("Вы уверены, что хотите удалить это задание? Это действие <b>необратимо</b>!", reply_markup=kb, parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data.regexp(r"^delete_job_confirm_\d+"))
async def delete_job(call: CallbackQuery):
    job_id = int(call.data.split('_')[-1])
    from services.job_service import get_job
    from core.db import async_session
    job = await get_job(job_id)
    if not job:
        try:
            await call.message.edit_text("Задание не найдено или уже удалено.", reply_markup=admin_main_menu(), parse_mode="HTML")
        except Exception:
            await call.message.answer("Задание не найдено или уже удалено.", reply_markup=admin_main_menu(), parse_mode="HTML")
        await call.answer()
        return
    # Удаляем сообщение в чате, если есть
    if hasattr(job, 'group_message_id') and job.group_message_id:
        from core.config import settings
        bot = call.bot
        try:
            await bot.delete_message(settings.WORKERS_CHAT_ID, job.group_message_id)
        except Exception:
            pass
    async with async_session() as session:
        await session.delete(job)
        await session.commit()
    try:
        await call.message.edit_text("🗑 <b>Задание удалено!</b>", parse_mode="HTML", reply_markup=admin_main_menu())
    except Exception:
        await call.message.answer("🗑 <b>Задание удалено!</b>", parse_mode="HTML", reply_markup=admin_main_menu())
    await call.answer() 