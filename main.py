import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# Загрузка переменных из .env
load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS").split(",")))

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Состояния
user_state = {}  # user_id -> "anon" / "open"
question_map = {}  # admin_msg_id -> {user_id, mode}

# Кнопки выбора
def get_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📩 Анонимно", callback_data="ask_anon")
    kb.button(text="✉️ Открыто", callback_data="ask_open")
    kb.adjust(1)
    return kb.as_markup()

# Стартовое сообщение
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        "Ассаляму алейкум ва рахматуллахи ва баракатуху ✨!\n\n"
        "Добро пожаловать в наш бот — место, где вы можете получить ответ на свой вопрос от уважаемых имамов и преподавателей.\n\n"
        "Выберите, как хотите отправить ваш вопрос:\n"
        "— 📩 Анонимно\n"
        "— ✉️ Открыто (с именем)\n\n"
        "Пусть Аллах сделает этот шаг благом для вас и уммы!",
        reply_markup=get_keyboard()
    )

# Обработка выбора режима
@dp.callback_query(F.data.in_({"ask_anon", "ask_open"}))
async def mode_selected(callback: types.CallbackQuery):
    mode = "anon" if callback.data == "ask_anon" else "open"
    user_state[callback.from_user.id] = mode
    await callback.message.answer(f"Отправьте свой {'анонимный' if mode == 'anon' else 'открытый'} вопрос.")
    await callback.answer()

# Основной обработчик сообщений
@dp.message()
async def handle_messages(message: types.Message):
    user_id = message.from_user.id

    # Защита от пустых сообщений
    if not message.text or message.text.strip() == "":
        await message.answer("Пожалуйста, напишите текст вопроса.")
        return

    # Защита от ответов бота самому себе
    if user_id == (await bot.me()).id:
        return

    # Обработка ответа от админа
    if message.reply_to_message and user_id in ADMIN_IDS:
        original_msg_id = message.reply_to_message.message_id
        if original_msg_id in question_map:
            target = question_map.pop(original_msg_id)
            await bot.send_message(target["user_id"], f"📨 Ответ наставника:\n{message.text}")
            await message.reply("✅ Ответ отправлен спрашивающему.")
        return

    # Обработка вопроса от пользователя
    if user_id in user_state:
        mode = user_state.pop(user_id)
        text = message.text

        for admin_id in ADMIN_IDS:
            try:
                if mode == "anon":
                    sent = await bot.send_message(
                        admin_id,
                        f"📩 <b>Анонимный вопрос:</b>\n\n{text}"
                    )
                else:
                    user_info = f"{message.from_user.full_name}"
                    if message.from_user.username:
                        user_info += f" (@{message.from_user.username})"
                    sent = await bot.send_message(
                        admin_id,
                        f"✉️ <b>Вопрос от {user_info}:</b>\n\n{text}"
                    )
                question_map[sent.message_id] = {"user_id": user_id, "mode": mode}
                logging.info(f"Вопрос от {user_id} отправлен админу {admin_id}")
            except Exception as e:
                logging.error(f"Ошибка при отправке админу {admin_id}: {e}")
                continue

        await message.answer("✅ Ваш вопрос отправлен. Ждите ответа.", reply_markup=get_keyboard())
    else:
        await message.answer("Пожалуйста, нажмите /start и выберите режим отправки вопроса.")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())