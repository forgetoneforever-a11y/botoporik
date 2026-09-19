# Полный список точных текстов всех кнопок с клавиатур
MENU_BUTTONS = [
    "🎲 Рандомное видео", "📂 Категории", "⚙️ Настройки", "🛠 Report",
    "📤 Загрузить видео", "📊 Статистика", "📢 Сделать рассылку (/all)", 
    "🗄 База данных", "🗄 База данных (Список)", "◀️ В главное меню"
]

@dp.message(Command("start"))
@dp.message(F.text & ~F.text.startswith("/") & ~F.in_(MENU_BUTTONS))
async def cmd_start_or_text(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Пользователь"
    
    if user_id not in user_settings:
        user_settings[user_id] = {"repeat": True, "shown_videos": set()}

    text = f"{user_name}, добрый день! Прочтите нашу осведомительную информацию /help! Это очень важный процесс!"
    
    if user_id in ADMIN_IDS:
        await message.answer(text, reply_markup=admin_kb())
    else:
        await message.answer(text, reply_markup=main_kb())
