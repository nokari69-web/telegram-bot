import asyncio
import aiosqlite
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    LabeledPrice,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

TOKEN = "8249125276:AAGbOWA12Oa1eO1AOHPE7K9dla_yDaApeV4"

CHANNEL_ID = -1003696808542
ADMIN_ID = 8145120188

bot = Bot(TOKEN)
dp = Dispatcher()

DB = "subs.db"


async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        expire_date TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        stars INTEGER
        )
        """)
        await db.commit()


@dp.message(Command("start"))
async def start(message: types.Message):

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Day ⭐666", callback_data="day")],
        [InlineKeyboardButton(text="Week ⭐1111", callback_data="week")],
        [InlineKeyboardButton(text="Month ⭐2222", callback_data="month")]
    ])

    await message.answer(
        "Choose your subscription:",
        reply_markup=kb
    )


@dp.callback_query(F.data.in_(["day", "week", "month"]))
async def buy(call: types.CallbackQuery):

    if call.data == "day":
        prices = [LabeledPrice(label="Day subscription", amount=666)]

    elif call.data == "week":
        prices = [LabeledPrice(label="Week subscription", amount=1111)]

    else:
        prices = [LabeledPrice(label="Month subscription", amount=2222)]

    await bot.send_invoice(
        chat_id=call.message.chat.id,
        title="VIP Subscription",
        description="Premium channel access",
        payload=call.data,
        provider_token=None,
        currency="XTR",
        prices=prices
    )


@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message(F.successful_payment)
async def payment_success(message: types.Message):

    payload = message.successful_payment.invoice_payload

    if payload == "day":
        expire = datetime.now() + timedelta(days=1)
        stars = 666

    elif payload == "week":
        expire = datetime.now() + timedelta(days=7)
        stars = 1111

    else:
        expire = datetime.now() + timedelta(days=30)
        stars = 2222

    async with aiosqlite.connect(DB) as db:

        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, expire_date) VALUES (?,?)",
            (message.from_user.id, expire.isoformat())
        )

        await db.execute(
            "INSERT INTO payments (user_id, stars) VALUES (?,?)",
            (message.from_user.id, stars)
        )

        await db.commit()

    invite = await bot.create_chat_invite_link(
        chat_id=CHANNEL_ID,
        member_limit=1
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Join VIP Channel", url=invite.invite_link)]
    ])

    await message.answer(
        "✅ Payment successful!\n\nClick below to join the VIP channel:",
        reply_markup=kb
    )


@dp.message(Command("status"))
async def status(message: types.Message):

    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT expire_date FROM users WHERE user_id=?",
            (message.from_user.id,)
        ) as cursor:

            row = await cursor.fetchone()

            if not row:
                await message.answer("❌ No subscription")
                return

            expire = datetime.fromisoformat(row[0])

            if expire > datetime.now():
                await message.answer(f"✅ Active until: {expire}")
            else:
                await message.answer("❌ Subscription expired")


@dp.message(Command("test"))
async def test(message: types.Message):

    invite = await bot.create_chat_invite_link(
        chat_id=CHANNEL_ID,
        member_limit=1
    )

    await message.answer(
        f"Test invite link:\n{invite.invite_link}"
    )


@dp.message(Command("users"))
async def users(message: types.Message):

    if message.from_user.id != ADMIN_ID:
        return

    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            count = await cursor.fetchone()

    await message.answer(f"Users with subscription: {count[0]}")


@dp.message(Command("revenue"))
async def revenue(message: types.Message):

    if message.from_user.id != ADMIN_ID:
        return

    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT SUM(stars) FROM payments") as cursor:
            total = await cursor.fetchone()

    stars = total[0] if total[0] else 0

    await message.answer(f"Total revenue: ⭐{stars}")


@dp.message(Command("give"))
async def give(message: types.Message):

    if message.from_user.id != ADMIN_ID:
        return

    try:
        _, user_id, days = message.text.split()

        user_id = int(user_id)
        days = int(days)

        expire = datetime.now() + timedelta(days=days)

        async with aiosqlite.connect(DB) as db:
            await db.execute(
                "INSERT OR REPLACE INTO users (user_id, expire_date) VALUES (?,?)",
                (user_id, expire.isoformat())
            )
            await db.commit()

        await message.answer("Subscription given")

    except:
        await message.answer("Usage: /give USER_ID DAYS")


async def check_subscriptions():

    while True:

        async with aiosqlite.connect(DB) as db:
            async with db.execute("SELECT user_id, expire_date FROM users") as cursor:

                rows = await cursor.fetchall()

                for user_id, expire_date in rows:

                    expire = datetime.fromisoformat(expire_date)

                    if expire < datetime.now():

                        try:
                            await bot.ban_chat_member(CHANNEL_ID, user_id)
                            await bot.unban_chat_member(CHANNEL_ID, user_id)
                        except:
                            pass

        await asyncio.sleep(600)


async def remind_subscriptions():

    while True:

        async with aiosqlite.connect(DB) as db:
            async with db.execute("SELECT user_id, expire_date FROM users") as cursor:

                rows = await cursor.fetchall()

                for user_id, expire_date in rows:

                    expire = datetime.fromisoformat(expire_date)

                    if expire - datetime.now() < timedelta(days=1) and expire > datetime.now():

                        try:
                            await bot.send_message(
                                user_id,
                                "⚠️ Your subscription will expire soon.\nRenew it to keep access."
                            )
                        except:
                            pass

        await asyncio.sleep(3600)


async def main():

    await init_db()

    asyncio.create_task(check_subscriptions())
    asyncio.create_task(remind_subscriptions())

    print("Bot started")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())