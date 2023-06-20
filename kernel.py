import logging
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher.filters import Text
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup
import sqlite3
from topics import topics_by_person, topics_by_project, topics_by_panzi, trending_hashtags
from credentials import TOKEN

# Configuring logging
logging.basicConfig(level=logging.INFO, filename='bot.log',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Handlers
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
conn = sqlite3.connect('webamooz.db')  # Your database connection

async def init_db():
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS registered_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                UNIQUE(topic, user_id)
            )
        """)

async def start_command(message: types.Message):
    logging.info('start_command initiated by user %s', message.from_user.id)
    keyboard_markup = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard_markup.add("👤 بر اساس افراد", "☢️ بر اساس پروژه و شرکت ها")
    keyboard_markup.row("♨️ بر اساس طرح های پانزی", "🔥 هشتگ های ترند")
    await message.answer("لطفاً یک دسته بندی را انتخاب کنید:", reply_markup=keyboard_markup)


async def show_topics_by(message: types.Message, topics_by, by_type):
    logging.info('show_topics_by initiated by user %s', message.from_user.id)
    keyboard_markup = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard_markup.add(*topics_by)
    keyboard_markup.row("🔙 بازگشت")
    await message.answer(f"{by_type}:\n\n" + "\n".join(topics_by), reply_markup=keyboard_markup)

async def handle_topic_selection(message: types.Message, state: FSMContext):
    logging.info('handle_topic_selection initiated by user %s', message.from_user.id)
    selected_topic = message.text
    keyboard_markup = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard_markup.add("👥 نویسندگان", "ثبت نام", "🔙 بازگشت")
    await state.update_data(selected_topic=selected_topic)
    await message.answer(f"شما موضوع {selected_topic} را انتخاب کرده‌اید. لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
                         reply_markup=keyboard_markup)

async def show_writers(message: types.Message, state: FSMContext):
    logging.info('show_writers initiated by user %s', message.from_user.id)
    data = await state.get_data()
    topic = data.get("selected_topic")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM registered_users WHERE topic=?", (topic,))
    rows = cursor.fetchall()
    if rows:
        writers_list = []
        for row in rows:
            chat = await bot.get_chat(row[0])
            writers_list.append(f"@{chat.username or 'anonymous'}")
        writers_str = '\n'.join(writers_list)
        await message.answer(f"نویسندگان ثبت‌نام شده برای {topic}:\n\n{writers_str}")
    else:
        await message.answer(f"هیچ نویسنده‌ای برای {topic} ثبت‌نام نکرده است")

async def register_topic(message: types.Message, state: FSMContext):
    logging.info('register_topic initiated by user %s', message.from_user.id)
    data = await state.get_data()
    topic = data.get("selected_topic")
    user_id = message.from_user.id
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO registered_users (topic, user_id) VALUES (?, ?)", (topic, user_id))
    conn.commit()
    if cursor.rowcount:
        await message.answer(f"ثبت نام شما برای {topic} با موفقیت انجام شد")
    else:
        await message.answer("شما قبلاً برای این موضوع ثبت نام کرده‌اید")

async def on_startup(dp):
    me = await bot.get_me()
    logging.info('Bot has started. Bot info: %s', me)
    logging.warning('Bot started in production mode')
    await init_db()


if __name__ == '__main__':
    from aiogram import executor

    dp.register_message_handler(start_command, commands=['start'])
    dp.register_message_handler(lambda message: show_topics_by(message, topics_by_person, "👤 بر اساس افراد"), Text(equals="👤 بر اساس افراد"))
    dp.register_message_handler(lambda message: show_topics_by(message, topics_by_project, "☢️ بر اساس پروژه و شرکت ها"), Text(equals="☢️ بر اساس پروژه و شرکت ها"))
    dp.register_message_handler(lambda message: show_topics_by(message, topics_by_panzi, "♨️ بر اساس طرح های پانزی"), Text(equals="♨️ بر اساس طرح های پانزی"))
    dp.register_message_handler(lambda message: show_topics_by(message, trending_hashtags, "🔥 هشتگ های ترند"), Text(equals="🔥 هشتگ های ترند"))
    dp.register_message_handler(handle_topic_selection, lambda message: message.text in topics_by_person or message.text in topics_by_project or message.text in topics_by_panzi or message.text in trending_hashtags)
    dp.register_message_handler(show_writers, Text(equals="👥 نویسندگان"))
    dp.register_message_handler(register_topic, Text(equals="ثبت نام"))
    dp.register_message_handler(start_command, Text(equals="🔙 بازگشت"))

    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
