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
from aiogram.types import ReplyKeyboardRemove

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

from datetime import datetime

from datetime import datetime

async def start_command(message: types.Message):
    logging.info('start_command initiated by user %s', message.from_user.id)
    
    # Getting the user's first name and the current hour
    first_name = message.from_user.first_name
    current_hour = datetime.now().hour

    # Determining the part of the day
    if 5 <= current_hour < 12:
        greeting = f"صبح بخیر, {first_name}!"
    elif 12 <= current_hour < 18:
        greeting = f"عصر بخیر, {first_name}!"
    else:
        greeting = f"شب بخیر, {first_name}!"
    
    # A sentence about security
    security_message = "امنیت اطلاعات شما برای ما از اهمیت بالایی برخوردار است. هیچ اطلاعاتی بدون رضایت شما ذخیره یا استفاده نمی‌شود."

    keyboard_markup = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard_markup.add("👤 بر اساس افراد", "☢️ بر اساس پروژه و شرکت ها")
    keyboard_markup.row("♨️ بر اساس طرح های پانزی", "🔥 هشتگ های ترند")
    keyboard_markup.add("📚 نویسندگان و موضوعات ثبت شده", "🚫 لغو ثبت نام در تمام موضوعات")  # Added a new button

    await message.answer(f"{greeting}\n\n{security_message}\n\nلطفاً یک دسته بندی را انتخاب کنید:", reply_markup=keyboard_markup)


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

async def deregister_all_topics(message: types.Message):
    logging.info('deregister_all_topics initiated by user %s', message.from_user.id)
    user_id = message.from_user.id
    cursor = conn.cursor()
    cursor.execute("DELETE FROM registered_users WHERE user_id=?", (user_id,))
    conn.commit()
    if cursor.rowcount:
        await message.answer("شما از تمام موضوعات لغو ثبت نام شدید.", reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer("شما در هیچ موضوعی ثبت نام نکرده‌اید.")

async def show_all_writers_with_topics(message: types.Message):
    logging.info('show_all_writers_with_topics initiated by user %s', message.from_user.id)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, topic FROM registered_users")
    rows = cursor.fetchall()
    if rows:
        message_str = ""
        for row in rows:
            chat = await bot.get_chat(row[0])
            username = "@" + (chat.username or 'anonymous')

            # Determine category
            if row[1] in topics_by_person:
                category = "بر اساس افراد"
            elif row[1] in topics_by_project:
                category = "بر اساس پروژه و شرکت ها"
            elif row[1] in topics_by_panzi:
                category = "بر اساس طرح های پانزی"
            elif row[1] in trending_hashtags:
                category = "هشتگ های ترند"
            else:
                category = "غیره"

            message_str += f"<b>Username:</b> {username}\n<b>Category:</b> {category}\n<b>Topic</b> {row[1]}\n\n"
        await bot.send_message(message.chat.id, f"نویسندگان و موضوعات:\n\n{message_str}", parse_mode='HTML')
    else:
        await bot.send_message(message.chat.id, "هیچ نویسنده و موضوعی ثبت‌نام نکرده است", parse_mode='HTML')



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
    dp.register_message_handler(show_all_writers_with_topics, Text(equals="📚 نویسندگان و موضوعات ثبت شده"))
    dp.register_message_handler(deregister_all_topics, Text(equals="🚫 لغو ثبت نام در تمام موضوعات"))  # Registering the new function as a handler

    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
