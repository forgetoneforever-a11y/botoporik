import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from database import get_all_videos, get_random_video, get_video_by_id, add_video
from aiohttp import web

# Читаем токен и ID администратора из переменных окружения
TOKEN = os.environ.get("BOT_TOKEN")
admin_id_str = os.environ.get("ADMIN_IDS", "8617178928")
ADMIN_IDS = [int(admin_id_str)]

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Словарь для хранения настроек пользователей (например, повторение видео: True/False)
# user_settings[user_id] = {"repeat": True, "shown_videos": set()}
user_settings = {}

class AdminStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_category = State()
    waiting_for_video = State()

class ReportStates(StatesGroup):
    waiting_for_report_text = State()

def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎲 Рандомное видео"), KeyboardButton(text="📂 Категории")],
            [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="🛠 Report")]
        ],
        resize_keyboard=True
    )

def admin_kb():
    kb = [
        [KeyboardButton(text="📤 Загрузить видео"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="🗄 База данных (Список)"), KeyboardButton(text="◀️ В главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# Обработка /start или любого первого сообщения
@dp.message(Command("start"))
@dp.message(F.text & ~F.text.startswith("/"))
async def cmd_start_or_text(message: types.Message):
    user_name = message.from_user.first_name or "Пользователь"
    
    # Инициализируем настройки пользователя, если их еще нет
    if message.from_user.id not in user_settings:
        user_settings[message.from_user.id] = {"repeat": True, "shown_videos": set()}

    if message.from_user.id in ADMIN_IDS:
        await message.answer(f"{user_name}, добрый день! Прочтите нашу осведомительную информацию /help! Это очень важный процесс!", reply_markup=admin_kb())
    else:
        await message.answer(f"{user_name}, добрый день! Прочтите нашу осведомительную информацию /help! Это очень важный процесс!", reply_markup=main_kb())

# Команда /help
@dp.message(Command("help"))
@dp.message(F.text == "ℹ️ Help")
async def cmd_help(message: types.Message):
    help_text = (
        "📖 **Справка по командам бота:**\n\n"
        "🎲 `/random` — отправка рандомного видеоматериала\n"
        "⚙️ `/setting` — настройки бота (включение/выключение повтора видео)\n"
        "🛠 `/report` — отправить ошибку администрации\n"
        "ℹ️ `/help` — показать эту справку"
    )
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(F.text == "◀️ В главное меню")
async def back_to_main(message: types.Message):
    await message.answer("Главное меню:", reply_markup=main_kb())

# Команда /random с учетом настроек повторения
@dp.message(Command("random"))
@dp.message(F.text == "🎲 Рандомное видео")
async def send_random(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_settings:
        user_settings[user_id] = {"repeat": True, "shown_videos": set()}
    
    settings = user_settings[user_id]
    all_videos = get_all_videos()
    
    if not all_videos:
        await message.answer("В базе пока нет видеороликов!")
        return
    
    # Если повтор выключен, фильтруем уже показанные видео
    if not settings["repeat"]:
        available_videos = [v for v in all_videos if v[0] not in settings["shown_videos"]]
        
        # Если все видео уже показаны, сбрасываем список
        if not available_videos:
            settings["shown_videos"].clear()
            available_videos = all_videos
            await message.answer("🔄 Все видео из базы уже были показаны! Список просмотренных сброшен.")
    else:
        available_videos = all_videos

    import random
    video = random.choice(available_videos)
    vid_id, title, category, file_id, file_url = video
    
    # Запоминаем, что видео показано
    settings["shown_videos"].add(vid_id)
    
    caption = f"🎬 **{title}**\n📂 Категория: {category}\n🆔 ID: `{vid_id}`"
    
    if file_id:
        await message.answer_video(video=file_id, caption=caption, parse_mode="Markdown")
    elif file_url:
        full_url = f"https://botoporik.onrender.com{file_url}"
        await message.answer_video(video=full_url, caption=caption, parse_mode="Markdown")

# Команда /setting (Настройки)
@dp.message(Command("setting"))
@dp.message(F.text == "⚙️ Настройки")
async def cmd_settings(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_settings:
        user_settings[user_id] = {"repeat": True, "shown_videos": set()}
    
    repeat_status = "Вкл ✅" if user_settings[user_id]["repeat"] else "Выкл ❌"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Повтор видео: {repeat_status}", callback_data="toggle_repeat")]
    ])
    await message.answer("⚙️ **Настройки бота:**\n\nВы можете включить или выключить повторение уже просмотренных видео при выборе рандома.", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "toggle_repeat")
async def toggle_repeat_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_settings:
        user_settings[user_id] = {"repeat": True, "shown_videos": set()}
    
    # Переключаем статус
    user_settings[user_id]["repeat"] = not user_settings[user_id]["repeat"]
    user_settings[user_id]["shown_videos"].clear()  # Сбрасываем историю при переключении
    
    repeat_status = "Вкл ✅" if user_settings[user_id]["repeat"] else "Выкл ❌"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Повтор видео: {repeat_status}", callback_data="toggle_repeat")]
    ])
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer("Настройки обновлены!")

# Команда /report (Сообщить об ошибке)
@dp.message(Command("report"))
@dp.message(F.text == "🛠 Report")
async def cmd_report_start(message: types.Message, state: FSMContext):
    await message.answer("Опишите вашу проблему или ошибку, и администрация получит ваше сообщение:")
    await state.set_state(ReportStates.waiting_for_report_text)

@dp.message(ReportStates.waiting_for_report_text)
async def process_report_text(message: types.Message, state: FSMContext):
    report_text = message.text
    user = message.from_user
    username = f"@{user.username}" if user.username else f"ID: {user.id}"
    
    # Пересылаем репорт администраторам
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, f"🚨 **Новый репорт об ошибке!**\nОт: {username} ({user.full_name})\n\nТекст:\n{report_text}", parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Не удалось отправить репорт админу {admin_id}: {e}")
            
    await message.answer("✅ Ваше сообщение успешно отправлено администрации! Спасибо.")
    await state.clear()

@dp.message(F.text == "📂 Категории")
async def show_categories(message: types.Message):
    videos = get_all_videos()
    categories = set(v[2] for v in videos)
    
    if not categories:
        await message.answer("Категории пока пустые.")
        return
        
    kb = []
    for cat in categories:
        kb.append([InlineKeyboardButton(text=cat, callback_data=f"cat_{cat}")])
        
    await message.answer("Выберите категорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("cat_"))
async def category_videos(callback: types.CallbackQuery):
    cat_name = callback.data.split("_", 1)[1]
    videos = [v for v in get_all_videos() if v[2] == cat_name]
    
    if not videos:
        await callback.message.answer(f"В категории **{cat_name}** пока нет видео.", parse_mode="Markdown")
        await callback.answer()
        return

    text = f"📹 Видео в категории **{cat_name}**:\n\n"
    for v in videos:
        text += f"• ID: `{v[0]}` | **{v[1]}**\n"
    
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.message(F.text == "📊 Статистика")
async def admin_stats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    videos = get_all_videos()
    await message.answer(f"📊 **Статистика бота:**\nВсего видео в базе: {len(videos)}", parse_mode="Markdown")

@dp.message(F.text == "🗄 База данных (Список)")
async def admin_database(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    videos = get_all_videos()
    if not videos:
        await message.answer("База данных пуста.")
        return
    for v in videos[:10]:
        await message.answer(f"ID: `{v[0]}`\nНазвание: **{v[1]}**\nКатегория: {v[2]}", parse_mode="Markdown")

@dp.message(F.text == "📤 Загрузить видео")
async def admin_upload_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    await message.answer("Введите название для нового видео:")
    await state.set_state(AdminStates.waiting_for_title)

@dp.message(AdminStates.waiting_for_title)
async def admin_get_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите категорию видео:")
    await state.set_state(AdminStates.waiting_for_category)

@dp.message(AdminStates.waiting_for_category)
async def admin_get_category(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer("Теперь отправьте сам видеофайл:")
    await state.set_state(AdminStates.waiting_for_video)

@dp.message(AdminStates.waiting_for_video, F.video)
async def admin_get_video_file(message: types.Message, state: FSMContext):
    data = await state.get_data()
    add_video(title=data['title'], category=data['category'], file_id=message.video.file_id)
    await message.answer("✅ Видеотека успешно пополнена!", reply_markup=admin_kb())
    await state.clear()

async def handle(request):
    return web.Response(text="Bot is running!")

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    logging.basicConfig(level=logging.INFO)
    asyncio.create_task(web_server())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
