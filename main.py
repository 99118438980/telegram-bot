import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS").split(",")))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

user_state = {}  # user_id -> "anon" / "open"
question_map = {}  # admin_msg_id -> {user_id, mode}

def get_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📩 Анонимно", callback_data="ask_anon")
    kb.button(text="✉️ Открыто", callback_data="ask_open")
    kb.adjust(1)
    return kb.as_markup()

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        "<b>Ассаляму алейкум ва рахматуЛлахи ва баракатуху ✨</b>\n\n"
        "Добро пожаловать в наш бот — <i>место, где вы можете получить достоверный ответ , мудрый совет и наставление</i> от уважаемых имамов преподавателей.\n\n"
        "<b>Выберите формат вопроса:</b>\n"
        "📩 — <b>Анонимно</b>\n"
        "✉️ — <b>Открыто</b> (с именем)\n\n"
        "<i>Пусть Аллах сделает этот проект благом для Уммы!</i>",
        reply_markup=get_keyboard()
    )

@dp.callback_query(F.data.in_({"ask_anon", "ask_open"}))
async def mode_selected(callback: types.CallbackQuery):
    mode = "anon" if callback.data == "ask_anon" else "open"
    user_state[callback.from_user.id] = mode
    await callback.message.answer(
        f"✍️ <b>Теперь отправьте ваш {'анонимный' if mode == 'anon' else 'открытый'} вопрос.</b>\n"
        "Вы можете прикрепить фото или видео, если это поможет!"
    )
    await callback.answer()

@dp.message()
async def handle_messages(message: types.Message):
    user_id = message.from_user.id

    # Ответ от администратора
    if message.reply_to_message and user_id in ADMIN_IDS:
        original_msg_id = message.reply_to_message.message_id
        if original_msg_id in question_map:
            target = question_map[original_msg_id]
            try:
                caption = (
                    "<b>📨 Ответ наставников:</b>\n\n"
                    f"{message.caption or message.text or ''}\n\n"
                    "<i>Пусть Аллах укрепит вас и направит к благому!</i>"
                )
                if message.photo:
                    await bot.send_photo(target["user_id"], message.photo[-1].file_id, caption=caption)
                elif message.video:
                    await bot.send_video(target["user_id"], message.video.file_id, caption=caption)
                else:
                    await bot.send_message(target["user_id"], caption)
                await message.reply("✅ <b>Ответ успешно отправлен.</b>")
            except Exception as e:
                logging.error(f"Ошибка при отправке ответа: {e}")
        return

    # Вопрос от пользователя
    if user_id in user_state:
        mode = user_state.pop(user_id)
        for admin_id in ADMIN_IDS:
            try:
                user_info = "<i>Анонимно</i>" if mode == "anon" else f"<b>{message.from_user.full_name}</b>"
                if mode == "open" and message.from_user.username:
                    user_info += f" (@{message.from_user.username})"
                caption = (
                    f"🕌 <b>Новый вопрос от {user_info}:</b>\n\n"
                    f"{message.caption or message.text or ''}"
                )
                if message.photo:
                    sent = await bot.send_photo(admin_id, message.photo[-1].file_id, caption=caption)
                elif message.video:
                    sent = await bot.send_video(admin_id, message.video.file_id, caption=caption)
                else:
                    sent = await bot.send_message(admin_id, caption)
                question_map[sent.message_id] = {"user_id": user_id, "mode": mode}
            except Exception as e:
                logging.error(f"Ошибка при отправке админу {admin_id}: {e}")
        await message.answer(
            "✅ <b>Ваш вопрос был отправлен!</b>\n"
            "Пожалуйста, наберитесь терпения, наставники скоро ответят, ин ша Аллах.",
            reply_markup=get_keyboard()
        )
    else:
        await message.answer(
            "⚠️ <b>Сначала нажмите /start и выберите формат вопроса.</b>"
        )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
