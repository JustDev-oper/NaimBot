from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def moderation_keyboard(tg_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"approve_{tg_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{tg_id}")
        ]
    ])

def admin_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🕵️‍♂️ Модерация", callback_data="moderation")],
        [InlineKeyboardButton(text="👥 Список пользователей", callback_data="users")],
        [InlineKeyboardButton(text="📝 Создать задание", callback_data="create_job")],
        [InlineKeyboardButton(text="📋 Список заданий", callback_data="job_list")],
        [InlineKeyboardButton(text="💸 Заявки на выплаты", callback_data="withdraw_requests")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Рассылка новостей", callback_data="admin_news")],
        [InlineKeyboardButton(text="🧑‍💼 Массовые действия", callback_data="admin_bulk")],
    ])

def admin_reply_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🛠 Админ-меню")]], resize_keyboard=True)

def job_users_keyboard(job_id, users):
    # Кнопки для каждого пользователя, чтобы снять с задания, плюс кнопка удалить задание
    kb = [[InlineKeyboardButton(text=f"🙍‍♂️ {u.fio or u.tg_id}", callback_data=f"remove_{job_id}_{u.tg_id}")] for u in users]
    kb.append([InlineKeyboardButton(text="🗑 Удалить задание", callback_data=f"delete_job_{job_id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def job_list_keyboard(jobs):
    # Кнопки для выбора задания
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📝 {j.title}", callback_data=f"job_{j.id}")] for j in jobs
    ])

def back_to_admin_menu():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_menu")]
    ])

confirm_news_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="news_confirm_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="news_confirm_no"),
        ]
    ]
) 