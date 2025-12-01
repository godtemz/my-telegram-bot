

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
import asyncio
import logging
import sqlite3

# Ваши данные
BOT_TOKEN = "7950925104:AAE9kQYLTKgPUfiOYK2iKAkvbqR0rxNTAYE"
ADMIN_ID = 6026610759

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Создаем объекты бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Подключаемся к базе данных
db_conn = sqlite3.connect("users.db", check_same_thread=False)
db_cursor = db_conn.cursor()

# Создаём таблицу, если её нет
db_cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        message_count INTEGER DEFAULT 0
    )
""")
db_conn.commit()

def get_user_link(user_id, username):
    if username:
        return f"@{username}"
    else:
        return f"[{user_id}](tg://user?id={user_id})"

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username

    # Записываем пользователя в базу (или обновляем, если уже есть)
    db_cursor.execute("INSERT OR IGNORE INTO users (user_id, username, message_count) VALUES (?, ?, 0)", (user_id, username))
    if username:
        db_cursor.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
    db_conn.commit()

    if user_id == ADMIN_ID:
        await message.answer("Привет, админ! Пересылайте сообщения пользователей сюда, ответив на них (reply).")
    else:
        # Отправляем пользователю красивое сообщение с цитатой и курсивом
        welcome_text = (
            "<i>Здравствуйте!\n\n"
            "Отправьте своё сообщение и мы ответим в ближайшее время.\n"
            "Это полностью анонимно 🎭\n\n"
            "<blockquote>Создано с помощью @ReFatherBot</blockquote></i>"
        )
        await message.answer(welcome_text, parse_mode="HTML")

@dp.message(Command("users"))
async def cmd_users(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    # Получаем всех пользователей, отсортированных по количеству сообщений
    db_cursor.execute("SELECT username, message_count FROM users ORDER BY message_count DESC")
    users = db_cursor.fetchall()

    if not users:
        await message.answer("Пока никто не запускал бота.")
        return

    response = "Список пользователей:\n\n"
    for username, msg_count in users:
        if username:
            response += f"• @{username} — {msg_count} сообщений\n"
        else:
            response += f"• (без юзернейма) — {msg_count} сообщений\n"

    await message.answer(response)

@dp.message(Command("cleanusers"))
async def cmd_cleanusers(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    # Очищаем таблицу
    db_cursor.execute("DELETE FROM users")
    db_conn.commit()
    await message.answer("База пользователей очищена.")

@dp.message()
async def handle_message(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username

    # Обновляем username и счётчик сообщений
    db_cursor.execute("INSERT OR IGNORE INTO users (user_id, username, message_count) VALUES (?, ?, 0)", (user_id, username))
    db_cursor.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
    db_cursor.execute("UPDATE users SET message_count = message_count + 1 WHERE user_id = ?", (user_id,))
    db_conn.commit()

    # Проверяем, является ли отправитель админом
    if user_id == ADMIN_ID:
        # Проверяем, является ли это ответом на сообщение
        if message.reply_to_message:
            replied_msg = message.reply_to_message
            original_text = replied_msg.text or ""

            # Ищем ID пользователя в формате: ID: <цифры>
            import re
            match = re.search(r'ID: (\d+)', original_text)
            if match:
                target_id = int(match.group(1))
                try:
                    # Отправляем то же самое, что отправил админ
                    if message.text:
                        await bot.send_message(target_id, message.text)
                    elif message.photo:
                        await bot.send_photo(target_id, message.photo[-1].file_id, caption=message.caption)
                    elif message.video:
                        await bot.send_video(target_id, message.video.file_id, caption=message.caption)
                    elif message.sticker:
                        await bot.send_sticker(target_id, message.sticker.file_id)
                    elif message.document:
                        await bot.send_document(target_id, message.document.file_id, caption=message.caption)
                    elif message.audio:
                        await bot.send_audio(target_id, message.audio.file_id, caption=message.caption)
                    elif message.voice:
                        await bot.send_voice(target_id, message.voice.file_id, caption=message.caption)
                    elif message.location:
                        await bot.send_location(target_id, message.location.latitude, message.location.longitude)
                    elif message.contact:
                        await bot.send_contact(target_id, phone_number=message.contact.phone_number, first_name=message.contact.first_name)
                    else:
                        await message.answer("Не могу переслать этот тип сообщения.")

                    await message.answer("Сообщение отправлено пользователю.")
                except Exception as e:
                    await message.answer(f"Ошибка при отправке: {e}")
        return

    # Если отправитель не админ — пересылаем админу
    user_link = get_user_link(user_id, username)
    user_info = f"Пользователь: {user_link}\nID: {user_id}"
    await bot.send_message(ADMIN_ID, user_info)

    # Отправляем админу само сообщение (любого типа)
    if message.text:
        await bot.send_message(ADMIN_ID, message.text)
    elif message.photo:
        await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=message.caption)
    elif message.video:
        await bot.send_video(ADMIN_ID, message.video.file_id, caption=message.caption)
    elif message.sticker:
        await bot.send_sticker(ADMIN_ID, message.sticker.file_id)
    elif message.document:
        await bot.send_document(ADMIN_ID, message.document.file_id, caption=message.caption)
    elif message.audio:
        await bot.send_audio(ADMIN_ID, message.audio.file_id, caption=message.caption)
    elif message.voice:
        await bot.send_voice(ADMIN_ID, message.voice.file_id, caption=message.caption)
    elif message.location:
        await bot.send_location(ADMIN_ID, message.location.latitude, message.location.longitude)
    elif message.contact:
        await bot.send_contact(ADMIN_ID, phone_number=message.contact.phone_number, first_name=message.contact.first_name)
    else:
        await bot.send_message(ADMIN_ID, "Получено сообщение неизвестного типа.")

    # Отправляем пользователю подтверждение и удаляем его через 2 секунды
    confirmation_msg = await message.answer("✅ Сообщение успешно отправлено")
    await asyncio.sleep(2)
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=confirmation_msg.message_id)
    except Exception:
        pass  # Игнорируем ошибку, если сообщение уже удалено или невозможно удалить

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        db_conn.close()
