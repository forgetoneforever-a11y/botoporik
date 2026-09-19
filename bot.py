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

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилище настроек и списка пользователей для рассылки
user_settings = {}

class AdminStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_category = State()
    waiting_for_video = State()
    waiting_for_broadcast = State()

class ReportStates(StatesGroup):
    waiting_for_report_text = State()

def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎲 Рандомное видео"), KeyboardButton(text="📂 Категории")],
            [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="🛠 Report")],
            [KeyboardButton(text="ℹ️ Помощь (/help)")],
        ],
        resize_keyboard=True
    )

def admin_kb():
    kb = [
        [KeyboardButton(text="📤 Загрузить видео"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="📢 Сделать рассылку (/all)"), KeyboardButton(text="🗄 База данных (Список)")],
        [KeyboardButton(text="🎲 Рандомное видео"), KeyboardButton(text="🛠 Report")],
        [KeyboardButton(text="◀️ В главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# Функция для автоудаления видео через 10 секунд
async def schedule_video_deletion(video_message, notification_message, delay=10):
    await asyncio.sleep(delay)
    try:
        await video_message.delete()
        await notification_message.delete()
    except Exception as e:
        logging.error(f"Не удалось удалить сообщение с видео: {e}")


# --- КОМАНДЫ И КНОПКИ МЕНЮ (ПЕРВЫЙ ПРИОРИТЕТ) ---

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

# Команда /help и кнопка помощи
@dp.message(Command("help"))
@dp.message(F.text == "ℹ️ Помощь (/help)")
async def cmd_help(message: types.Message):
    help_text = (
        "📖 **Справка по командам бота:**\n\n"
        "🎲 `/random` — отправка рандомного видеоматериала\n"
        "⚙️ `/setting` — настройки бота (повтор видео вкл/выкл)\n"
        "🛠 `/report` — отправить ошибку администрации\n"
        "ℹ️ `/help` — показать эту справку"
    )
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(F.text == "◀️ В главное меню")
async def back_to_main(message: types.Message):
    user_id = message.from_user.id
    if user_id in ADMIN_IDS:
        await message.answer("Главное меню администратора:", reply_markup=admin_kb())
    else:
        await message.answer("Главное меню:", reply_markup=main_kb())

# Команда /random с отправкой видео, уведомлением и автоудалением через 10 секунд
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
    
    if not settings["repeat"]:
        available_videos = [v for v in all_videos if v[0] not in settings["shown_videos"]]
        if not available_videos:
            settings["shown_videos"].clear()
            available_videos = all_videos
            await message.answer("🔄 Все видео из базы уже были показаны! Список просмотренных сброшен.")
    else:
        available_videos = all_videos

    import random
    video = random.choice(available_videos)
    vid_id, title, category, file_id, file_url = video
    
    settings["shown_videos"].add(vid_id)
    
    caption = f"🎬 **{title}**\n📂 Категория: {category}\n🆔 ID: `{vid_id}`"
    
    try:
        if file_id:
            sent_video = await message.answer_video(video=file_id, caption=caption, parse_mode="Markdown")
        elif file_url:
            full_url = f"https://botoporik.onrender.com{file_url}"
            sent_video = await message.answer_video(video=full_url, caption=caption, parse_mode="Markdown")
        
        notif_msg = await message.answer("⏳ Это видео автоматически удалится через 10 секунд.")
        asyncio.create_task(schedule_video_deletion(sent_video, notif_msg, 10))
    except Exception as e:
        await message.answer(f"Ошибка при отправке видео: {e}")

# Настройки (/setting)
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
    await message.answer("⚙️ **Настройки бота:**\n\nЕсли повтор выключен, видео не будут повторяться, пока вы не просмотрите всю базу.", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "toggle_repeat")
async def toggle_repeat_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_settings:
        user_settings[user_id] = {"repeat": True, "shown_videos": set()}
    
    user_settings[user_id]["repeat"] = not user_settings[user_id]["repeat"]
    user_settings[user_id]["shown_videos"].clear()
    
    repeat_status = "Вкл ✅" if user_settings[user_id]["repeat"] else "Выкл ❌"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Повтор видео: {repeat_status}", callback_data="toggle_repeat")]
    ])
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer("Настройки обновлены!")

# Обратная связь / Report (Связь с администрацией)
@dp.message(Command("report"))
@dp.message(F.text == "🛠 Report")
async def cmd_report_start(message: types.Message, state: FSMContext):
    await message.answer("Опишите вашу проблему, предложение или ошибку, и администрация сразу получит ваше сообщение:")
    await state.set_state(ReportStates.waiting_for_report_text)

@dp.message(ReportStates.waiting_for_report_text)
async def process_report_text(message: types.Message, state: FSMContext):
    report_text = message.text
    user = message.from_user
    username = f"@{user.username}" if user.username else f"ID: {user.id}"
    
    reply_kb = None
    if user.username:
        reply_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Написать пользователю", url=f"https://t.me/{user.username}")]
        ])

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id, 
                f"🚨 **Новое обращение в поддержку (Report)!**\nОт: {username} ({user.full_name})\nID: `{user.id}`\n\nТекст:\n{report_text}", 
                reply_markup=reply_kb,
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Не удалось отправить репорт админу {admin_id}: {e}")
            
    await message.answer("✅ Ваше сообщение успешно отправлено администрации! Спасибо за обратную связь.")
    await state.clear()

# Рассылка администратора через /all
@dp.message(Command("all"))
@dp.message(F.text == "📢 Сделать рассылку (/all)")
async def admin_broadcast_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("📢 Введите текст или отправьте контент для рассылки всем пользователям:")
    await state.set_state(AdminStates.waiting_for_broadcast)

@dp.message(AdminStates.waiting_for_broadcast)
async def admin_execute_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    success_count = 0
    fail_count = 0
    
    for uid in user_settings.keys():
        try:
            await message.send_copy(chat_id=uid)
            success_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            fail_count += 1
            
    await message.answer(f"📢 **Рассылка завершена!**\n✅ Успешно доставлено: {success_count}\n❌ Ошибок отправки: {fail_count}", parse_mode="Markdown")
    await state.clear()

# Категории
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
    await message.answer(f"📊 **Статистика бота:**\nВсего видео в базе: {len(videos)}\nАктивных пользователей в сессии: {len(user_settings)}", parse_mode="Markdown")

@dp.message(F.text == "🗄 База данных (Список)")
@dp.message(F.text == "🗄 База данных")
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


# --- ОБРАБОТКА ОБЫЧНОГО ТЕКСТА (В САМОМ КОНЦЕ) ---

@dp.message(F.text & ~F.text.startswith("/"))
async def catch_other_text(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Пользователь"
    
    if user_id not in user_settings:
        user_settings[user_id] = {"repeat": True, "shown_videos": set()}

    text = f"{user_name}, добрый день! Прочтите нашу осведомительную информацию /help! Это очень важный процесс!"
    
    if user_id in ADMIN_IDS:
        await message.answer(text, reply_markup=admin_kb())
    else:
        await message.answer(text, reply_markup=main_kb())


# --- ВЕБ-СЕРВЕР И ОТДАЧА HTML САЙТА ---

async def handle(request):
    try:
        return web.FileResponse('./index.html')
    except Exception:
        return web.Response(text="Bot is running! (index.html not found)")

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
