from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from services.job_service import get_jobs, apply_for_job
from keyboards.user import user_main_menu
import calendar

RU_MONTHS = [
    '', 'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
]

router = Router()


@router.callback_query(F.data == "jobs")
async def show_jobs_cb(call: CallbackQuery):
    jobs = await get_jobs()
    if not jobs:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="close_notify")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        await call.message.answer("Список заданий пока пуст", reply_markup=kb)
        await call.answer()
        return
    for job in jobs:
        text = f"<b>{job.title}</b>\n{job.description}\nОплата: {job.pay}\nНужно работников: {job.workers_needed}\nЗаписано: {len(job.workers.split(',')) if job.workers else 0}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✋ Откликнуться", callback_data=f"apply_{job.id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"), InlineKeyboardButton(text="❌ Закрыть", callback_data="close_notify")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        if job.photo:
            await call.message.answer_photo(job.photo, caption=text, reply_markup=kb)
        else:
            await call.message.answer(text, reply_markup=kb)
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
        await call.answer(f"❗️Ваш возраст не подходит для этого задания! (допустимо: {job.min_age}-{job.max_age})",
                          show_alert=True)
        return
    ok = await apply_for_job(job_id, call.from_user.id)
    if ok:
        await call.answer("Вы успешно откликнулись на задание!", show_alert=True)
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
            text = (f"<b>📝 Новое задание!</b>\n"
                    f"<b>Название:</b> {job.title}\n"
                    f"<b>Описание:</b> {job.description}\n"
                    f"<b>Адрес:</b> {job.address}\n"
                    f"<b>Оплата:</b> {job.pay} ₽\n"
                    f"<b>Возраст:</b> {job.min_age} - {job.max_age if job.max_age != 99 else 'без ограничений'}\n"
                    f"<b>Время:</b> {date_str}\n"
                    f"<b>Мест:</b> {total}\n"
                    f"<b>Свободно:</b> {places}")
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✋ Записаться", callback_data=f"apply_{job.id}")]
            ])
            try:
                await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                pass
    else:
        await call.answer("Не удалось откликнуться (возможно, вы уже записаны или мест нет)", show_alert=True)
