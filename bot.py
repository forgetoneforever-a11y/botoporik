# --- ХЕНДЛЕРЫ КНОПОК И КОМАНД (ПЕРВЫЙ ПРИОРИТЕТ) ---

@dp.message(F.text == "◀️ В главное меню")
async def back_to_main(message: types.Message):
    user_id = message.from_user.id
    if user_id in ADMIN_IDS:
        await message.answer("Главное меню администратора:", reply_markup=admin_kb())
    else:
        await message.answer("Главное меню:", reply_markup=main_kb())

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Пользователь"
    
    if user_id not in user_settings:
        user_settings[user_id] = {"repeat": True, "shown_videos": set()}

    text = f"{user_name}, добрый день! Прочтите нашу осведомительную информацию /help! Это очень важный процесс!"
    
    if user_id in ADMIN_IDS:
        await message.answer(text, reply_markup=admin_kb())
    else:
        await message.answer(text, reply_markup=main_kb())

# Команда /help
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "📖 **Справка по командам бота:**\n\n"
        "🎲 `/random` — отправка рандомного видеоматериала\n"
        "⚙️ `/setting` — настройки бота (повтор видео вкл/выкл)\n"
        "🛠 `/report` — отправить ошибку администрации\n"
        "ℹ️ `/help` — показать эту справку"
    )
    await message.answer(help_text, parse_mode="Markdown")
