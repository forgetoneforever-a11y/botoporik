import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from database import get_all_videos, get_random_video, get_video_by_id, add_video

# Укажите ваш токен бота и Telegram ID администратора(-ов)
TOKEN = "YOUR_BOT_TOKEN"
ADMIN_IDS = [123456789]  # Замените на свой Telegram ID

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Состояния для FSM (загрузка видео через админку бота)
class AdminStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_category = State()
    waiting_for_video = State()

# Главная клавиатура пользователя
def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎲 Рандомное видео"), KeyboardButton(text="📂 Категории")],
            [KeyboardButton(text="ℹ️ О боте")]
        ],
        resize_keyboard=True
    )

# Клавиатура администратора
def admin_kb():
    kb = [
        [KeyboardButton(text="📤 Загрузить видео"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="🗄 База данных (Список)"), KeyboardButton(text="◀️ В главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("Привет, администратор! Вам доступна админ-панель.", reply_markup=admin_kb())
    else:
        await message.answer("Привет! Выбирай действие:", reply_markup=main_kb())

@dp.message(F.text == "◀️ В главное меню")
async def back_to_main(message: types.Message):
    await message.answer("Главное меню:", reply_markup=main_kb())

# --- Рандомное видео ---
@dp.message(F.text == "🎲 Рандомное видео")
@dp.message(Command("random"))
async def send_random(message: types.Message):
    video = get_random_video()
    if not video:
        await message.answer("В базе пока нет видеороликов!")
        return
    
    vid_id, title, category, file_id, file_url = video
    caption = f"🎬 **{title}**\n📂 Категория: {category}\n🆔 ID: `{vid_id}`"
    
    if file_id:
        await message.answer_video(video=file_id, caption=caption, parse_mode="Markdown")
    elif file_url:
        # Если видео загружено через сайт, отправляем по прямой ссылке или хосту
        full_url = f"http://127.0.0.1:5000{file_url}" # Замените на домен сайта в продакшене
        await message.answer_video(video=full_url, caption=caption, parse_mode="Markdown")

# --- Категории ---
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
    
    text = f"📹 Видео в категории **{cat_name}**:\n\n"
    for v in videos:
        text += f"• ID: `{v[0]}` | **{v[1]}**\n"
    
    text += "\nЧтобы посмотреть видео, введите его ID или воспользуйтесь поиском /id <номер>"
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

# --- Админ-панель: Статистика и База данных ---
@dp.message(F.text == "📊 Статистика")
async def admin_stats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    videos = get_all_videos()
    await message.answer(f"📊 **Статистика бота:**\nВсего видео в базе: {len(videos)}", parse_mode="Markdown")

@dp.message(F.text == "🗄 База данных (Список)")
async def admin_database(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    videos = get_all_videos()
    
    if not videos:
        await message.answer("База данных пуста.")
        return
        
    for v in videos[:10]: # Выводим по 10 штук, чтобы не спамить
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Скопировать ID-команду", callback_data=f"getid_{v[0]}")]
        ])
        await message.answer(f"ID: `{v[0]}`\nНазвание: **{v[1]}**\nКатегория: {v[2]}", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("getid_"))
async def callback_get_id(callback: types.CallbackQuery):
    vid_id = callback.data.split("_")[1]
    await callback.answer(f"ID видео: {vid_id}. Пользователи могут найти его по этому номеру!", show_alert=True)

# --- Админ-панель: Загрузка через бота ---
@dp.message(F.text == "📤 Загрузить видео")
async def admin_upload_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    await message.answer("Введите название для нового видео:")
    await state.set_state(AdminStates.waiting_for_title)

@dp.message(AdminStates.waiting_for_title)
async def admin_get_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите категорию видео (например: Юмор, Игры):")
    await state.set_state(AdminStates.waiting_for_category)

@dp.message(AdminStates.waiting_for_category)
async def admin_get_category(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer("Теперь отправьте сам видеофайл:")
    await state.set_state(AdminStates.waiting_for_video)

@dp.message(AdminStates.waiting_for_video, F.video)
async def admin_get_video_file(message: types.Message, state: FSMContext):
    data = await state.get_data()
    title = data['title']
    category = data['category']
    file_id = message.video.file_id
    
    add_video(title=title, category=category, file_id=file_id)
    await message.answer("✅ Видеотека успешно пополнена!", reply_markup=admin_kb())
    await state.clear()

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())