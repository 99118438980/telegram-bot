import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from aiohttp import web  # Новый импорт

# Загрузка .env
load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS").split(",")))

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Создание бота и диспетчера
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Память
user_state = {}  # user_id -> "anon" / "open"
question_map = {}  # admin_msg_id -> {user_id, mode}

# Кнопки
def get_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📩 Анонимно", callback_data="ask_anon")
    kb.button(text="✉️ Открыто", callback_data="ask_open")
    kb.adjust(1)
    return kb.as_markup()

# Команда /start
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        "Ассаляму алейкум ва рахматуллахи ва баракатуху ✨!\n"
        "Добро пожаловать в наш бот — место, где вы можете получить ответ на свой вопрос от уважаемых имамов и преподавателей.\n\n"
        "<b>Выберите, как хотите отправить ваш вопрос:</b>\n"
        "— Анонимно\n"
        "— Открыто (с именем)\n\n"
        "Пусть Аллах сделает этот проект благом Уммы!",
        reply_markup=get_keyboard()
    )

# Обработка кнопок
@dp.callback_query(F.data.in_({"ask_anon", "ask_open"}))
async def mode_selected(callback: types.CallbackQuery):
    mode = "anon" if callback.data == "ask_anon" else "open"
    user_state[callback.from_user.id] = mode
    await callback.message.answer(
        f"Отправьте свой {'анонимный' if mode == 'anon' else 'открытый'} вопрос."
    )
    await callback.answer()

# Получение вопроса и обработка ответов
@dp.message()
async def handle_messages(message: types.Message):
    user_id = message.from_user.id

    # Ответ от админа
    if message.reply_to_message and user_id in ADMIN_IDS:
        original_msg_id = message.reply_to_message.message_id
        if original_msg_id in question_map:
            target = question_map[original_msg_id]
            try:
                await bot.send_message(target["user_id"], f"📨 Ответ наставников:\n{message.text}")
                await message.reply("✅ Ответ отправлен спрашивающему.")
            except Exception as e:
                logging.error(f"Ошибка при отправке ответа пользователю: {e}")
        return

    # Вопрос от пользователя
    if user_id in user_state:
        mode = user_state.pop(user_id)
        text = message.text

        for admin_id in ADMIN_IDS:
            try:
                if mode == "anon":
                    sent = await bot.send_message(
                        admin_id,
                        f"📩 <b>Анонимный вопрос:</b>\n\n{text}",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    user_info = f"{message.from_user.full_name}"
                    if message.from_user.username:
                        user_info += f" (@{message.from_user.username})"
                    sent = await bot.send_message(
                        admin_id,
                        f"✉️ <b>Вопрос от {user_info}:</b>\n\n{text}",
                        parse_mode=ParseMode.HTML
                    )
                question_map[sent.message_id] = {"user_id": user_id, "mode": mode}
            except Exception as e:
                logging.error(f"Ошибка при отправке админу {admin_id}: {e}")
                continue

        await message.answer(
            "✅ Ваш вопрос отправлен. Ждите ответа.",
            reply_markup=get_keyboard()
        )
    else:
        await message.answer("Пожалуйста, нажмите /start и выберите режим.")

# HTTP-сервер для Render/UptimeRobot
async def handle(request):
    return web.Response(text="Bot is alive")

async def start_web_app():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8080)))
    await site.start()

# Запуск
async def main():
    await asyncio.gather(
        start_web_app(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
