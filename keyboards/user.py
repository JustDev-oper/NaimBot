from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def user_main_menu(is_subscribed=True):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = [
        [InlineKeyboardButton(text="💼 Подработка", callback_data="jobs")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
    ]
    if is_subscribed:
        buttons.append([InlineKeyboardButton(text="🔕 Отписаться от новых заданий", callback_data="unsubscribe_jobs")])
    else:
        buttons.append([InlineKeyboardButton(text="🔔 Подписаться на новые задания", callback_data="subscribe_jobs")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def user_reply_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🏠 Главное меню")]], resize_keyboard=True)

def user_profile_keyboard():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Вывести средства", callback_data="withdraw")],
        [InlineKeyboardButton(text="📊 История баланса", callback_data="balance_history")],
        [InlineKeyboardButton(text="💸 Мои заявки на вывод", callback_data="my_withdraw_requests")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="close_notify")]
    ]) 