import os
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

PAGE_SIZE = 5
DB_FILE = "songs.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            file_id TEXT NOT NULL
        )
    """)
    return conn

def get_categories():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT DISTINCT category FROM songs ORDER BY category")
    rows = [r[0] for r in cur.fetchall()]
    db.close()
    return rows

def get_songs(category, page):
    offset = (page - 1) * PAGE_SIZE
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT id, title FROM songs WHERE category=? ORDER BY id LIMIT ? OFFSET ?",
        (category, PAGE_SIZE, offset)
    )
    rows = cur.fetchall()
    db.close()
    return rows

async def start(message: Message):
    kb = InlineKeyboardBuilder()
    for cat in get_categories():
        kb.button(text=cat, callback_data=f"cat:{cat}:1")
    await message.answer("🎵 Выбери категорию:", reply_markup=kb.as_markup())

async def add_song_from_admin(message: Message):
    if not message.audio or not message.caption:
        return
    if "|" not in message.caption:
        await message.reply("Формат: Категория | Название")
        return
    category, title = [x.strip() for x in message.caption.split("|", 1)]
    db = get_db()
    db.execute(
        "INSERT INTO songs(title, category, file_id) VALUES (?,?,?)",
        (title, category, message.audio.file_id)
    )
    db.commit()
    db.close()
    await message.reply("✅ Песня добавлена")

async def category_click(call: CallbackQuery):
    _, category, page = call.data.split(":")
    page = int(page)
    songs = get_songs(category, page)

    kb = InlineKeyboardBuilder()
    for song_id, title in songs:
        kb.button(text=title, callback_data=f"play:{song_id}")

    if page > 1:
        kb.button(text="⬅️ Назад", callback_data=f"cat:{category}:{page-1}")
    if len(songs) == PAGE_SIZE:
        kb.button(text="➡️ Далее", callback_data=f"cat:{category}:{page+1}")

    await call.message.edit_text(f"🎶 {category}:", reply_markup=kb.as_markup())

async def play_song(call: CallbackQuery):
    song_id = int(call.data.split(":")[1])
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT file_id FROM songs WHERE id=?", (song_id,))
    row = cur.fetchone()
    db.close()
    if row:
        await call.message.answer_audio(row[0])

async def main():
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()

    dp.message.register(start, CommandStart())
    dp.message.register(add_song_from_admin, F.audio)
    dp.callback_query.register(category_click, F.data.startswith("cat:"))
    dp.callback_query.register(play_song, F.data.startswith("play:"))

    await dp.start_polling(bot)

if name == "main":
    asyncio.run(main())
