from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from services.job_service import get_jobs, apply_for_job
from keyboards.user import user_main_menu
import calendar
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandObject, Command

RU_MONTHS = [
    '', 'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
]

router = Router()


@router.callback_query(F.data == "jobs")
async def show_jobs_cb(call: CallbackQuery, state: FSMContext):
    jobs = await get_jobs()
    if not jobs:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        try:
            await call.message.edit_text("Список заданий пока пуст 😔", reply_markup=kb)
        except Exception:
            await call.message.answer("Список заданий пока пуст 😔", reply_markup=kb)
        await call.answer()
        return
    await state.update_data(jobs=[job.id for job in jobs], job_index=0)
    # show_job теперь всегда edit (edit=True)
    await show_job(call, state, jobs, 0, edit=True)
    await call.answer()


async def show_job(call, state, jobs, index, edit=True):
    from services.job_service import get_job
    job_id = jobs[index] if isinstance(jobs[index], int) else jobs[index].id
    job = await get_job(job_id)
    # Форматируем дату и время
    day = job.start_time.day
    month = RU_MONTHS[job.start_time.month]
    start_time_str = job.start_time.strftime('%H:%M')
    end_time_str = job.end_time.strftime('%H:%M')
    date_str = f"{day} {month} {start_time_str} - {end_time_str}"
    taken = len(job.workers.split(',')) if job.workers else 0
    free = job.workers_needed - taken
    places = ' '.join(['🟩'] * free + ['🟥'] * taken)
    text = (
        f"<b>📝 {job.title}</b>\n\n"
        f"<b>📄 Описание:</b> {job.description}\n"
        f"<b>📍 Адрес:</b> {job.address}\n"
        f"<b>💸 Оплата:</b> <b>{job.pay} ₽</b>\n"
        f"<b>👤 Возраст:</b> от {job.min_age} - {('до ' + str(job.max_age)) if job.max_age != 99 else 'без ограничений'}\n"
        f"<b>🕒 Время:</b> {date_str}\n\n"
        f"<b>👥 Мест всего:</b> {job.workers_needed}\n\n"
        f"<b>Свободно:</b> {places}\n"
        f"<b>Записано:</b> {taken}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⬅️", callback_data="job_prev"),
            InlineKeyboardButton(text="✅ Откликнуться", callback_data=f"apply_{job.id}"),
            InlineKeyboardButton(text="➡️", callback_data="job_next")
        ],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    if job.photo:
        if edit:
            try:
                await call.message.edit_caption(caption=text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                await call.message.answer_photo(job.photo, caption=text, reply_markup=kb, parse_mode="HTML")
        else:
            await call.message.answer_photo(job.photo, caption=text, reply_markup=kb, parse_mode="HTML")
    else:
        if edit:
            try:
                await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                await call.message.answer(text, reply_markup=kb, parse_mode="HTML")
        else:
            await call.message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.in_(["job_prev", "job_next"]))
async def job_pagination(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    jobs = data.get("jobs", [])
    index = data.get("job_index", 0)
    if not jobs:
        await call.answer("❗️ Нет заданий", show_alert=True)
        return
    if call.data == "job_prev":
        index = (index - 1) % len(jobs)
    else:
        index = (index + 1) % len(jobs)
    await state.update_data(job_index=index)
    await show_job(call, state, jobs, index, edit=True)
    await call.answer()


@router.callback_query(F.data == "close_notify")
async def close_notify(call: CallbackQuery):
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.answer()


@router.callback_query(F.data.startswith("apply_"))
async def apply_job(call: CallbackQuery):
    job_id = int(call.data.split("_")[1])
    from services.job_service import get_job
    job = await get_job(job_id)
    from services.user_service import get_or_create_user
    user = await get_or_create_user(call.from_user.id)
    if user.age is None or user.age < job.min_age or user.age > job.max_age:
        await call.answer(f"❗️Ваш возраст не подходит для этого задания! (допустимо: {job.min_age}-{job.max_age})", show_alert=True)
        return
    ok = await apply_for_job(job_id, call.from_user.id)
    if ok:
        await call.answer("✅ Вы успешно откликнулись на задание!", show_alert=True)
        # Обновляем сообщение в группе
        from core.config import settings
        if settings.WORKERS_CHAT_ID and call.message.chat.id == settings.WORKERS_CHAT_ID:
            # Получаем актуальные данные о job после записи
            job = await get_job(job_id)
            total = job.workers_needed
            ids = job.workers.split(',') if job.workers else []
            taken = len(ids)
            free = total - taken
            places = ' '.join(['🟥'] * taken + ['🟩'] * free)
            # Форматируем дату и время
            day = job.start_time.day
            month = RU_MONTHS[job.start_time.month]
            start_time_str = job.start_time.strftime('%H:%M')
            end_time_str = job.end_time.strftime('%H:%M')
            date_str = f"{day} {month} {start_time_str} - {end_time_str}"
            text = (
                f"<b>📝 {job.title}</b>\n\n"
                f"<b>📄 Описание:</b> {job.description}\n"
                f"<b>📍 Адрес:</b> {job.address}\n"
                f"<b>💸 Оплата:</b> <b>{job.pay} ₽</b>\n"
                f"<b>👤 Возраст:</b> от {job.min_age} - {('до ' + str(job.max_age)) if job.max_age != 99 else 'без ограничений'}\n"
                f"<b>🕒 Время:</b> {date_str}\n\n"
                f"<b>👥 Мест всего:</b> {job.workers_needed}\n\n"
                f"<b>Свободно:</b> {places}\n"
                f"<b>Записано:</b> {taken}"
            )
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✋ Записаться", callback_data=f"apply_{job.id}")]
            ])
            try:
                await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                pass
    else:
        await call.answer("❌ Не удалось откликнуться (возможно, вы уже записаны или мест нет)", show_alert=True)


@router.message(Command("start"))
async def handle_deep_link(message: Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    if len(args) == 2 and args[1].startswith('job_'):
        try:
            job_id = int(args[1].split('_')[1])
        except Exception:
            await message.answer("Некорректная ссылка.")
            return
        from services.job_service import get_job
        job = await get_job(job_id)
        if not job:
            await message.answer('Задание не найдено.')
            return
        # Формируем текст задания (аналогично show_job)
        day = job.start_time.day
        month = RU_MONTHS[job.start_time.month]
        start_time_str = job.start_time.strftime('%H:%M')
        end_time_str = job.end_time.strftime('%H:%M')
        date_str = f"{day} {month} {start_time_str} - {end_time_str}"
        taken = len(job.workers.split(',')) if job.workers else 0
        free = job.workers_needed - taken
        places = ' '.join(['🟩'] * free + ['🟥'] * taken)
        text = (
            f"<b>📝 {job.title}</b>\n\n"
            f"<b>📄 Описание:</b> {job.description}\n"
            f"<b>📍 Адрес:</b> {job.address}\n"
            f"<b>💸 Оплата:</b> <b>{job.pay} ₽</b>\n"
            f"<b>👤 Возраст:</b> от {job.min_age} - {('до ' + str(job.max_age)) if job.max_age != 99 else 'без ограничений'}\n"
            f"<b>🕒 Время:</b> {date_str}\n\n"
            f"<b>👥 Мест всего:</b> {job.workers_needed}\n\n"
            f"<b>Свободно:</b> {places}\n"
            f"<b>Записано:</b> {taken}"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Записаться", callback_data=f"apply_{job.id}"), InlineKeyboardButton(text="❌ Закрыть", callback_data="close_notify")]
        ])
        if job.photo:
            await message.answer_photo(job.photo, caption=text, reply_markup=kb, parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        # Обычный /start, если нужно, можно ничего не делать или вызвать стандартный старт
        pass
