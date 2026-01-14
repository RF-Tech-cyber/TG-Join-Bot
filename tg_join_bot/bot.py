import os
import sqlite3
from pyrogram import Client, filters
from pyrogram.types import ChatJoinRequest

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS").split(",")))

app = Client(
    "join_guard_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

db = sqlite3.connect("users.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    username TEXT,
    shown INTEGER DEFAULT 0,
    blocked INTEGER DEFAULT 0
)
""")
db.commit()

# 📥 Join request handler
@app.on_chat_join_request()
async def join_request(client, request: ChatJoinRequest):
    user = request.from_user

    cursor.execute("SELECT blocked FROM users WHERE user_id = ?", (user.id,))
    data = cursor.fetchone()

    # ❌ Block rejoin
    if data and data[0] == 1:
        await request.decline()
        return

    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    username = user.username or "N/A"

    cursor.execute("""
    INSERT OR IGNORE INTO users (user_id, name, username)
    VALUES (?, ?, ?)
    """, (user.id, name, username))

    # Block future re-joins
    cursor.execute(
        "UPDATE users SET blocked = 1 WHERE user_id = ?",
        (user.id,)
    )

    db.commit()

    # Optional
    # await request.approve()

# 🔐 Admin-only /new
@app.on_message(filters.command("new") & filters.private)
async def new_users(client, message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Unauthorized")
        return

    cursor.execute("SELECT user_id, name, username FROM users WHERE shown = 0")
    users = cursor.fetchall()

    if not users:
        await message.reply("✅ No new users")
        return

    text = "🆕 **New Users:**\n\n"

    for u in users:
        text += f"👤 {u[1]}\n🆔 `{u[0]}`\n🔗 @{u[2]}\n\n"
        cursor.execute("UPDATE users SET shown = 1 WHERE user_id = ?", (u[0],))

    db.commit()
    await message.reply(text)

# 🔓 /unblock user_id
@app.on_message(filters.command("unblock") & filters.private)
async def unblock_user(client, message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Unauthorized")
        return

    if len(message.command) != 2:
        await message.reply("Usage:\n/unblock user_id")
        return

    user_id = int(message.command[1])

    cursor.execute(
        "UPDATE users SET blocked = 0 WHERE user_id = ?",
        (user_id,)
    )
    db.commit()

    await message.reply(f"✅ User `{user_id}` unblocked")

app.run()
