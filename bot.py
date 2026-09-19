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

class AdminStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_category = State()
    waiting_for_video = State()

def main_kb():
    # Кнопка "ℹ️ О боте" полностью удалена
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎲 Рандомное видео"), KeyboardButton(text="📂 Категории")]
        ],
        resize_keyboard=True
    )

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
        full_url = f"https://botoporik.onrender.com{file_url}"
        await message.answer_video(video=full_url, caption=caption, parse_mode="Markdown")

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
        await message.answer(f"ID: `{v[0]}`\nНазвание: **{v[1]}**\nКатегория: {v[2]}", parse_mode="Markdown", parse_mode_fallback=True)

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
