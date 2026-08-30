import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

import asyncio
import html
import random
import sqlite3
import time
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

DB_FILE = "fenya.db"
TICK_SECONDS = 40 * 60
LOOTBOX_PRICE = 30
DUPLICATE_COINS = 10
CASINO_BASE_STAKE = 20
CASINO_STAKE_STEP = 1
CASINO_STAKE_EVERY = 10

CAT_HAPPY = """\
 /\\_/\\
( ⚫ᴗ⚫)
 > ^ <  ♥
"""
CAT_OK = """\
 /\\_/\\
( ⚫_⚫)
 > ^ <
"""
CAT_SAD = """\
 /\\_/\\
( ⚫︵⚫)
 > ^ <
"""
CAT_SLEEP = """\
 /\\_/\\
( - . -) zZ
 > ^ <
"""
CAT_DIRTY = """\
 /\\_/\\
( ⚫~⚫)
 > ^ <  💨
"""

SKINS = {
    "gentleman": {"name": "🎩 Феня-джентльмен", "rarity": "Обычный", "weight": 15, "art": " /\\_/\\\n( ⚫_⚫)\n >🎩<\n"},
    "vampire": {"name": "🧛 Феня-вампир", "rarity": "Обычный", "weight": 15, "art": " /\\_/\\\n( 🔴_🔴)\n > ^ < 🧛\n"},
    "glasses": {"name": "😎 Феня в очках", "rarity": "Обычный", "weight": 15, "art": " /\\_/\\\n( 😎_😎)\n > ^ <\n"},
    "superhero": {"name": "🦸 Феня-супергерой", "rarity": "Редкий", "weight": 11, "art": " /\\_/\\\n( ⚫_⚫)\n >🦸<\n"},
    "witch": {"name": "🧙 Феня-ведьма", "rarity": "Редкий", "weight": 11, "art": " /\\_/\\\n( 🟢_🟢)\n >🧙<\n"},
    "royal": {"name": "👑 Королевская Феня", "rarity": "Редкий", "weight": 11, "art": "   👑\n /\\_/\\\n( ⚫ᴗ⚫)\n > ^ <\n"},
    "moon": {"name": "🌙 Лунная Феня", "rarity": "Редкий", "weight": 11, "art": "   🌙\n /\\_/\\\n( 🔵_🔵)\n > ^ <\n"},
    "rainbow": {"name": "🌈 Радужная Феня", "rarity": "Эпический", "weight": 8, "art": " /\\_/\\\n( 🌈_🌈)\n > ^ < ✨\n"},
    "ghost": {"name": "👻 Призрачная Феня", "rarity": "Эпический", "weight": 8, "art": " /\\_/\\\n( ⬜_⬜)\n > ^ < 👻\n"},
    "dragon": {"name": "🐉 Феня-дракон", "rarity": "Эпический", "weight": 7, "art": " /\\_/\\\n( 🟢_🟢)\n > ^ < 🐉\n"},
    "lightning": {"name": "⚡ Феня-молния", "rarity": "Эпический", "weight": 7, "art": " /\\_/\\\n( ⚡_⚡)\n > ^ <\n"},
    "diamond": {"name": "💎 Алмазная Феня", "rarity": "Легендарный", "weight": 3, "art": " /\\_/\\\n( 💎_💎)\n > ^ < ✨\n"},
    "cosmic": {"name": "🌌 Космическая Феня", "rarity": "Легендарный", "weight": 3, "art": " /\\_/\\\n( 🌟_🌟)\n > ^ < 🌌\n"},
    "forest": {"name": "🌲 Лесная Феня", "rarity": "Легендарный", "weight": 3, "art": " /\\_/\\\n( 🟢_🟢)\n > ^ < 🌲\n"},
    "mushroom": {"name": "🍄 Грибная Феня", "rarity": "Легендарный", "weight": 3, "art": " /\\_/\\\n( 🟤_🟤)\n >🍄<\n"},
    "magic": {"name": "🔮 Магическая Феня", "rarity": "Легендарный", "weight": 3, "art": " /\\_/\\\n( 🟣_🟣)\n > ^ < 🔮\n"},
    "phoenix": {"name": "🔥 Феня-феникс", "rarity": "Мифический", "weight": 1, "art": " /\\_/\\\n( 🔥_🔥)\n > ^ < 🔥\n"},
}

TITLES_BY_RANK = {
    1: "МГЕ Браток",
    2: "Второй в паровозике",
    3: "Замыкающий в паровозике",
}

EVENTS = [
    {"name": "🤑 Золотая неделя", "desc": "Монеты ×2", "type": "coins_x2"},
    {"name": "🍗 Праздник живота", "desc": "Корм +20%", "type": "food_up"},
    {"name": "🧶 Неделя тыгыдыка", "desc": "Игрушки ×2", "type": "toys_up"},
    {"name": "💩 Неделя пакостей", "desc": "Уборка ×3 монет", "type": "poop_up"},
    {"name": "🎰 Азартная неделя", "desc": "Шанс на 50 монет выше", "type": "casino_lucky"},
    {"name": "🎁 Неделя подарков", "desc": "Подарки дешевле", "type": "gifts_cheap"},
    {"name": "✨ Магическая неделя", "desc": "Редкие скины чаще", "type": "magic_skins"},
    {"name": "💤 Сонная неделя", "desc": "Энергия тратится медленнее", "type": "sleepy_week"},
]


def clamp(value: int) -> int:
    return max(0, min(100, value))


def connect_db():
    db = sqlite3.connect(DB_FILE)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = connect_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS cats (
            user_id INTEGER PRIMARY KEY,
            hunger INTEGER,
            mood INTEGER,
            energy INTEGER,
            clean INTEGER,
            love INTEGER,
            coins INTEGER,
            last_tick INTEGER,
            last_gift INTEGER,
            created_at INTEGER,
            last_play INTEGER DEFAULT 0,
            equipped_skin TEXT DEFAULT '',
            username TEXT DEFAULT '',
            display_name TEXT DEFAULT '',
            super_fenya_until INTEGER DEFAULT 0,
            casino_spins INTEGER DEFAULT 0,
            casino_spin_date TEXT DEFAULT '',
            last_wash INTEGER DEFAULT 0
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            user_id INTEGER,
            code TEXT,
            PRIMARY KEY (user_id, code)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            item_type TEXT,
            item_code TEXT,
            PRIMARY KEY (user_id, item_type, item_code)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            name TEXT,
            desc TEXT,
            type TEXT,
            started_at TEXT
        )
    """)
    for extra in (
        "ALTER TABLE cats ADD COLUMN last_play INTEGER DEFAULT 0",
        "ALTER TABLE cats ADD COLUMN equipped_skin TEXT DEFAULT ''",
        "ALTER TABLE cats ADD COLUMN username TEXT DEFAULT ''",
        "ALTER TABLE cats ADD COLUMN display_name TEXT DEFAULT ''",
        "ALTER TABLE cats ADD COLUMN super_fenya_until INTEGER DEFAULT 0",
        "ALTER TABLE cats ADD COLUMN casino_spins INTEGER DEFAULT 0",
        "ALTER TABLE cats ADD COLUMN casino_spin_date TEXT DEFAULT ''",
        "ALTER TABLE cats ADD COLUMN last_wash INTEGER DEFAULT 0",
    ):
        try:
            db.execute(extra)
        except sqlite3.OperationalError:
            pass
    db.commit()
    db.close()


def get_cat(user_id: int):
    db = connect_db()
    row = db.execute("SELECT * FROM cats WHERE user_id = ?", (user_id,)).fetchone()
    db.close()
    return row


def create_cat(user_id: int):
    now = int(time.time())
    db = connect_db()
    db.execute("""
        INSERT INTO cats (
            user_id, hunger, mood, energy, clean, love, coins,
            last_tick, last_gift, created_at, last_play, equipped_skin
        ) VALUES (?, 70, 70, 80, 90, 20, 100, ?, 0, ?, 0, '')
    """, (user_id, now, now))
    db.commit()
    db.close()


def save_cat(cat):
    db = connect_db()
    db.execute("""
        UPDATE cats SET
            hunger = ?, mood = ?, energy = ?, clean = ?, love = ?,
            coins = ?, last_tick = ?, last_gift = ?, last_play = ?,
            equipped_skin = ?, username = ?, display_name = ?,
            super_fenya_until = ?, casino_spins = ?, casino_spin_date = ?,
            last_wash = ?
        WHERE user_id = ?
    """, (
        cat["hunger"], cat["mood"], cat["energy"], cat["clean"], cat["love"],
        cat["coins"], cat["last_tick"], cat["last_gift"], cat.get("last_play", 0),
        cat.get("equipped_skin") or "", cat.get("username") or "",
        cat.get("display_name") or "", cat.get("super_fenya_until", 0),
        cat.get("casino_spins", 0), cat.get("casino_spin_date", ""),
        cat.get("last_wash", 0), cat["user_id"],
    ))
    db.commit()
    db.close()


def cat_to_dict(row) -> dict:
    return dict(row)


def is_super_fenya(cat: dict) -> bool:
    return cat.get("super_fenya_until", 0) > int(time.time())


def apply_time(cat: dict) -> dict:
    now = int(time.time())
    passed = now - cat["last_tick"]
    ticks = passed // TICK_SECONDS
    if ticks > 0:
        if not is_super_fenya(cat):
            cat["hunger"] = clamp(cat["hunger"] - 7 * ticks)
            cat["mood"] = clamp(cat["mood"] - 3 * ticks)
            cat["energy"] = clamp(cat["energy"] - 4 * ticks)
            cat["clean"] = clamp(cat["clean"] - 5 * ticks)
        cat["last_tick"] += ticks * TICK_SECONDS
        save_cat(cat)
    return cat


def load_cat(user_id: int):
    row = get_cat(user_id)
    if row is None:
        return None
    return apply_time(cat_to_dict(row))


def has_achievement(user_id: int, code: str) -> bool:
    db = connect_db()
    row = db.execute("SELECT 1 FROM achievements WHERE user_id = ? AND code = ?", (user_id, code)).fetchone()
    db.close()
    return row is not None


def give_achievement(user_id: int, code: str) -> bool:
    if has_achievement(user_id, code):
        return False
    db = connect_db()
    db.execute("INSERT INTO achievements (user_id, code) VALUES (?, ?)", (user_id, code))
    db.commit()
    db.close()
    return True


def list_achievements(user_id: int):
    db = connect_db()
    rows = db.execute("SELECT code FROM achievements WHERE user_id = ?", (user_id,)).fetchall()
    db.close()
    return [r["code"] for r in rows]


def has_skin(user_id: int, code: str) -> bool:
    db = connect_db()
    row = db.execute("SELECT 1 FROM inventory WHERE user_id = ? AND item_type = 'skin' AND item_code = ?", (user_id, code)).fetchone()
    db.close()
    return row is not None


def remove_skin(user_id: int, code: str):
    db = connect_db()
    db.execute("DELETE FROM inventory WHERE user_id = ? AND item_type = 'skin' AND item_code = ?", (user_id, code))
    db.commit()
    db.close()


def find_skin_code(text: str) -> str | None:
    key = text.lower().strip()
    if key in SKINS:
        return key
    for code, skin in SKINS.items():
        if key in skin["name"].lower():
            return code
    return None


def top_cats(limit: int = 10):
    db = connect_db()
    rows = db.execute("SELECT user_id, love, coins, username, display_name FROM cats ORDER BY love DESC, coins DESC LIMIT ?", (limit,)).fetchall()
    db.close()
    return rows


def add_skin(user_id: int, code: str):
    db = connect_db()
    db.execute("INSERT OR IGNORE INTO inventory (user_id, item_type, item_code) VALUES (?, 'skin', ?)", (user_id, code))
    db.commit()
    db.close()


def list_skins(user_id: int) -> list[str]:
    db = connect_db()
    rows = db.execute("SELECT item_code FROM inventory WHERE user_id = ? AND item_type = 'skin'", (user_id,)).fetchall()
    db.close()
    return [r["item_code"] for r in rows]


def roll_skin() -> str:
    codes = list(SKINS.keys())
    weights = [SKINS[code]["weight"] for code in codes]
    return random.choices(codes, weights=weights, k=1)[0]


def get_current_event() -> dict | None:
    db = connect_db()
    row = db.execute("SELECT name, desc, type, started_at FROM events WHERE id = 1").fetchone()
    db.close()
    return dict(row) if row else None


def set_current_event(event: dict):
    db = connect_db()
    db.execute("DELETE FROM events WHERE id = 1")
    db.execute("INSERT INTO events (id, name, desc, type, started_at) VALUES (1, ?, ?, ?, ?)",
               (event["name"], event["desc"], event["type"], datetime.now().isoformat()))
    db.commit()
    db.close()


def maybe_roll_event():
    event = get_current_event()
    now = datetime.now()
    if event:
        started = datetime.fromisoformat(event["started_at"])
        if now.isocalendar()[1] == started.isocalendar()[1] and now.isocalendar()[0] == started.isocalendar()[0]:
            return event
    new_event = random.choice(EVENTS)
    set_current_event(new_event)
    return new_event


def event_modifier(event_type: str, action: str) -> float:
    event = get_current_event()
    if not event:
        return 1.0
    if event["type"] == "coins_x2" and action in ("clean", "wash", "play", "sleep"):
        return 2.0
    if event["type"] == "food_up" and action == "feed":
        return 1.2
    if event["type"] == "toys_up" and action == "play":
        return 2.0
    if event["type"] == "poop_up" and action == "clean":
        return 3.0
    if event["type"] == "sleepy_week" and action == "sleep":
        return 1.5
    return 1.0


def inventory_keyboard(user_id: int, equipped: str) -> InlineKeyboardMarkup | None:
    owned = list_skins(user_id)
    if not owned:
        return None
    rows = []
    for code in owned:
        skin = SKINS.get(code)
        if not skin:
            continue
        mark = " ✓" if code == equipped else ""
        rows.append([InlineKeyboardButton(text=f"Надеть {skin['name']}{mark}", callback_data=f"eq:{code}")])
    rows.append([InlineKeyboardButton(text="Снять скин", callback_data="eq:off")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def check_achievements(cat: dict) -> list[str]:
    user_id = cat["user_id"]
    new_ones = []
    rules = [
        ("first_steps", "Первые шаги", True),
        ("love_50", "Феня тебя любит", cat["love"] >= 50),
        ("love_100", "Лучшие друзья", cat["love"] >= 100),
        ("rich", "Богач", cat["coins"] >= 500),
        ("full", "Сытая кошка", cat["hunger"] >= 100),
        ("clean", "Чистюля", cat["clean"] >= 100),
        ("energy", "Полный заряд", cat["energy"] >= 100),
        ("happy", "Счастливая Феня", cat["mood"] >= 100),
    ]
    age_hours = (int(time.time()) - cat["created_at"]) / 3600
    rules.append(("day", "День вместе", age_hours >= 24))
    for code, title, ok in rules:
        if ok and give_achievement(user_id, code):
            new_ones.append(title)
    return new_ones


def bar(value: int) -> str:
    filled = round(value / 10)
    return "█" * filled + "░" * (10 - filled) + f" {value}"


def cat_art(cat: dict) -> str:
    skin_code = cat.get("equipped_skin") or ""
    if skin_code in SKINS:
        return SKINS[skin_code]["art"]
    if is_super_fenya(cat):
        return " /\\_/\\\n( ✨_✨)\n > 💧 <\n"
    if cat["energy"] < 20:
        return CAT_SLEEP
    if cat["clean"] < 25:
        return CAT_DIRTY
    if cat["mood"] >= 70 and cat["hunger"] >= 50:
        return CAT_HAPPY
    if cat["mood"] < 30 or cat["hunger"] < 20:
        return CAT_SAD
    return CAT_OK


def status_text(cat: dict) -> str:
    art = html.escape(cat_art(cat))
    skin_code = cat.get("equipped_skin") or ""
    if is_super_fenya(cat):
        title = "💧 Супер-Феня (жидкий корм)"
    elif skin_code in SKINS:
        title = SKINS[skin_code]["name"]
    else:
        title = "🖤 <b>Феня</b>"
    super_left = ""
    if is_super_fenya(cat):
        left = cat["super_fenya_until"] - int(time.time())
        hours = left // 3600
        minutes = (left % 3600) // 60
        super_left = f"\n⏳ Осталось: {hours} ч {minutes} мин"
    return (
        f"<pre>{art}</pre>\n"
        f"{title}{super_left}\n\n"
        f"🍗 Сытость: {bar(cat['hunger'])}\n"
        f"😸 Настроение: {bar(cat['mood'])}\n"
        f"⚡ Энергия: {bar(cat['energy'])}\n"
        f"✨ Чистота: {bar(cat['clean'])}\n"
        f"❤️ Любовь: {bar(cat['love'])}\n\n"
        f"💰 Монеты: {cat['coins']}"
    )


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🍗 Покормить"), KeyboardButton(text="🧶 Поиграть")],
            [KeyboardButton(text="🪠 Убрать лоток"), KeyboardButton(text="🧼 Помыть ковёр")],
            [KeyboardButton(text="✋ Погладить"), KeyboardButton(text="🛏 Уложить спать")],
            [KeyboardButton(text="📊 Статус"), KeyboardButton(text="🛒 Магазин")],
            [KeyboardButton(text="🎰 Казино"), KeyboardButton(text="🎁 Лутбокс")],
            [KeyboardButton(text="🏆 Достижения"), KeyboardButton(text="🎁 Подарки")],
        ],
        resize_keyboard=True,
    )


def need_cat(message: Message):
    return load_cat(message.from_user.id)


bot = Bot(BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    if get_cat(user_id) is None:
        create_cat(user_id)
        text = (
            "Привет! Я <b>Фенягочи</b> 🖤\n\n"
            "У тебя появилась чёрная кошка <b>Феня</b>.\n"
            "Корми её, гладь, играй и не забывай про лоток.\n\n"
            "Каждые 40 минут Феня немного устаёт и голодает — заглядывай почаще!"
        )
    else:
        text = "Феня уже ждёт тебя 🖤"
    maybe_roll_event()
    cat = load_cat(user_id)
    await message.answer(text, parse_mode="HTML", reply_markup=main_keyboard())
    await message.answer(status_text(cat), parse_mode="HTML")


async def reply_with_cat(message: Message, extra: str, cat: dict):
    extra_ach = check_achievements(cat)
    text = extra + "\n\n" + status_text(cat)
    if extra_ach:
        text += "\n\n🏆 Новое достижение: " + ", ".join(extra_ach)
    await message.answer(text, parse_mode="HTML", reply_markup=main_keyboard())


@dp.message(F.text == "📊 Статус")
async def btn_status(message: Message):
    cat = need_cat(message)
    if cat is None:
        await message.answer("Напиши /start, чтобы завести Феню.")
        return
    await message.answer(status_text(cat), parse_mode="HTML")


@dp.message(F.text == "🍗 Покормить")
async def btn_feed(message: Message):
    cat = need_cat(message)
    if cat is None:
        await message.answer("Напиши /start, чтобы завести Феню.")
        return
    if cat["coins"] < 10:
        await message.answer("Не хватает монет. Корм стоит 10 💰")
        return
    cat["coins"] -= 10
    cat["hunger"] = clamp(cat["hunger"] + 20)
    cat["mood"] = clamp(cat["mood"] + 5)
    save_cat(cat)
    give_achievement(cat["user_id"], "first_steps")
    await reply_with_cat(message, "Феня с аппетитом съела корм 🍗", cat)


@dp.message(F.text == "🧶 Поиграть")
async def btn_play(message: Message):
    cat = need_cat(message)
    if cat is None:
        await message.answer("Напиши /start, чтобы завести Феню.")
        return
    now = int(time.time())
    if now - cat.get("last_play", 0) < TICK_SECONDS:
        await message.answer("Феня только что играла. Попробуй позже.")
        return
    if cat["energy"] < 15:
        await message.answer("Феня слишком устала. Уложи её спать 🛏")
        return
    cat["mood"] = clamp(cat["mood"] + 18)
    cat["energy"] = clamp(cat["energy"] - 12)
    cat["hunger"] = clamp(cat["hunger"] - 5)
    cat["love"] = clamp(cat["love"] + 4)
    cat["last_play"] = now
    cat["coins"] += 5
    save_cat(cat)
    await reply_with_cat(message, "Феня гоняет клубок по комнате 🧶", cat)


@dp.message(F.text == "🪠 Убрать лоток")
async def btn_clean(message: Message):
    cat = need_cat(message)
    if cat is None:
        await message.answer("Напиши /start, чтобы завести Феню.")
        return
    cat["clean"] = clamp(cat["clean"] + 25)
    cat["mood"] = clamp(cat["mood"] + 8)
    cat["coins"] += 10
    save_cat(cat)
    await reply_with_cat(message, "Лоток чистый. Феня довольно мурчит 🪠", cat)


@dp.message(F.text == "🧼 Помыть ковёр")
async def btn_wash(message: Message):
    cat = need_cat(message)
    if cat is None:
        await message.answer("Напиши /start, чтобы завести Феню.")
        return
    now = int(time.time())
    if now - cat.get("last_wash", 0) < TICK_SECONDS:
        await message.answer("Ковёр ещё чистый. Попробуй позже.")
        return
    cat["clean"] = clamp(cat["clean"] + 30)
    cat["coins"] += 15
    cat["last_wash"] = now
    save_cat(cat)
    await reply_with_cat(message, "Ковёр чистый! Феня смотрит с уважением 🧼", cat)


@dp.message(F.text == "✋ Погладить")
async def btn_pet(message: Message):
    cat = need_cat(message)
    if cat is None:
        await message.answer("Напиши /start, чтобы завести Феню.")
        return
    if random.random() < 0.2 and cat["love"] < 50:
        await message.answer("Феня испугалась и убежала 🙀")
        return
    cat["love"] = clamp(cat["love"] + 10)
    cat["mood"] = clamp(cat["mood"] + 10)
    save_cat(cat)
    await reply_with_cat(message, "Феня трётся о руку и мурлычет ✋", cat)


@dp.message(F.text == "🛏 Уложить спать")
async def btn_sleep(message: Message):
    cat = need_cat(message)
    if cat is None:
        await message.answer("Напиши /start, чтобы завести Феню.")
        return
    cat["energy"] = clamp(cat["energy"] + 30)
    cat["hunger"] = clamp(cat["hunger"] - 8)
    cat["coins"] += 5
    save_cat(cat)
    await reply_with_cat(message, "Феня свернулась клубочком и заснула 🛏", cat)


SHOP = {
    "1": {"name": "🐟 Рыбка", "price": 25, "hunger": 35, "mood": 5},
    "2": {"name": "🐭 Игрушка-мышь", "price": 30, "mood": 30, "love": 5},
    "3": {"name": "🧴 Шампунь", "price": 20, "clean": 40},
    "4": {"name": "🛏 Подушка", "price": 25, "energy": 35},
    "5": {"name": "🍬 Лакомство", "price": 40, "love": 15, "mood": 10},
}


@dp.message(F.text == "🛒 Магазин")
async def btn_shop(message: Message):
    cat = need_cat(message)
    if cat is None:
        await message.answer("Напиши /start, чтобы завести Феню.")
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 — 🐟 Рыбка (25💰)", callback_data="buy:1")],
            [InlineKeyboardButton(text="2 — 🐭 Игрушка-мышь (30💰)", callback_data="buy:2")],
            [InlineKeyboardButton(text="3 — 🧴 Шампунь (20💰)", callback_data="buy:3")],
            [InlineKeyboardButton(text="4 — 🛏 Подушка (25💰)", callback_data="buy:4")],
            [InlineKeyboardButton(text="5 — 🍬 Лакомство (40💰)", callback_data="buy:5")],
        ]
    )
    await message.answer(
        f"🛒 <b>Магазин для Фени</b>\nУ тебя {cat['coins']} 💰\n\nВыбери товар:",
        parse_mode="HTML",
        reply_markup=kb,
    )


@dp.callback_query(F.data.startswith("buy:"))
async def cb_buy(callback: CallbackQuery):
    cat = load_cat(callback.from_user.id)
    if cat is None:
        await callback.answer("Сначала /start")
        return
    code = callback.data.split(":", 1)[1]
    item = SHOP[code]
    if cat["coins"] < item["price"]:
        await callback.answer(f"Не хватает монет. Нужно {item['price']} 💰")
        return
    cat["coins"] -= item["price"]
    for key in ("hunger", "mood", "energy", "clean", "love"):
        if key in item:
            cat[key] = clamp(cat[key] + item[key])
    save_cat(cat)
    await callback.answer(f"Куплено: {item['name']}")
    await callback.message.answer(status_text(cat), parse_mode="HTML")


@dp.message(F.text == "🎰 Казино")
async def btn_casino(message: Message):
    cat = need_cat(message)
    if cat is None:
        await message.answer("Напиши /start, чтобы завести Феню.")
        return
    today = datetime.now().date().isoformat()
    if cat.get("casino_spin_date") != today:
        cat["casino_spins"] = 0
        cat["casino_spin_date"] = today
    stake = CASINO_BASE_STAKE + (cat["casino_spins"] // CASINO_STAKE_EVERY) * CASINO_STAKE_STEP
    await message.answer(
        "🎰 <b>КотоДжек</b>\n"
        f"Баланс: {cat['coins']} 💰\n"
        f"Текущая ставка: {stake} 💰\n\n"
        "Напиши <code>крутить</code> — испытать удачу!\n"
        "Шансы: 40% — 0, 40% — 5, 10% — 10, 9% — 50, 1% — 💧 Жидкий корм.",
        parse_mode="HTML",
    )


@dp.message(F.text.lower() == "крутить")
async def casino_bet(message: Message):
    cat = need_cat(message)
    if cat is None:
        await message.answer("Напиши /start, чтобы завести Феню.")
        return
    today = datetime.now().date().isoformat()
    if cat.get("casino_spin_date") != today:
        cat["casino_spins"] = 0
        cat["casino_spin_date"] = today
    stake = CASINO_BASE_STAKE + (cat["casino_spins"] // CASINO_STAKE_EVERY) * CASINO_STAKE_STEP
    if cat["coins"] < stake:
        await message.answer(f"Не хватает монет. Ставка: {stake} 💰")
        return

    cat["coins"] -= stake
    cat["casino_spins"] += 1

    roll = random.random()
    if roll < 0.01:
        if is_super_fenya(cat):
            cat["super_fenya_until"] = cat["super_fenya_until"] + 24 * 60 * 60
        else:
            cat["super_fenya_until"] = int(time.time()) + 24 * 60 * 60
        cat["hunger"] = 100
        cat["mood"] = 100
        cat["energy"] = 100
        cat["clean"] = 100
        result = "💧 ЖИДКИЙ КОРМ «ЛОСОСЬ»! Супер-Феня на 24 часа!"
    elif roll < 0.10:
        win = 50
        cat["coins"] += win
        result = f"Выигрыш: {win} 💰"
    elif roll < 0.20:
        win = 10
        cat["coins"] += win
        result = f"Выигрыш: {win} 💰"
    elif roll < 0.60:
        win = 5
        cat["coins"] += win
        result = f"Выигрыш: {win} 💰"
    else:
        result = "Феня грустно смотрит на барабаны... 0 💰"

    save_cat(cat)
    await reply_with_cat(message, f"🎰 {result}", cat)


@dp.message(Command("top"))
async def cmd_top(message: Message):
    rows = top_cats(10)
    if not rows:
        await message.answer("Пока никого нет. Напиши /start")
        return
    lines = ["🏆 <b>Рейтинг игроков</b>\n"]
    for index, row in enumerate(rows, start=1):
        name = row["display_name"] or row["username"] or f"id{row['user_id']}"
        title = TITLES_BY_RANK.get(index, "Нейрослоп машина")
        lines.append(f"{index}. {name} — ❤️{row['love']} 💰{row['coins']} ({title})")
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(Command("event"))
async def cmd_event(message: Message):
    event = maybe_roll_event()
    await message.answer(f"📅 <b>Ивент недели:</b> {event['name']}\n{event['desc']}", parse_mode="HTML")


ACHIEVEMENT_TITLES = {
    "first_steps": "Первые шаги — начать ухаживать за Феней",
    "love_50": "Феня тебя любит — любовь 50+",
    "love_100": "Лучшие друзья — любовь 100",
    "rich": "Богач — 500 монет",
    "full": "Сытая кошка — сытость 100",
    "clean": "Чистюля — чистота 100",
    "energy": "Полный заряд — энергия 100",
    "happy": "Счастливая Феня — настроение 100",
    "day": "День вместе — 24 часа с Феней",
}


@dp.message(F.text == "🏆 Достижения")
async def btn_achievements(message: Message):
    cat = need_cat(message)
    if cat is None:
        await message.answer("Напиши /start, чтобы завести Феню.")
        return
    check_achievements(cat)
    owned = set(list_achievements(message.from_user.id))
    lines = ["🏆 <b>Достижения</b>\n"]
    for code, title in ACHIEVEMENT_TITLES.items():
        mark = "✅" if code in owned else "⬜"
        lines.append(f"{mark} {title}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(F.text == "🎁 Подарки")
async def btn_gifts(message: Message):
    cat = need_cat(message)
    if cat is None:
        await message.answer("Напиши /start, чтобы завести Феню.")
        return
    now = int(time.time())
    day = 24 * 60 * 60
    if now - cat["last_gift"] < day:
        left = day - (now - cat["last_gift"])
        hours = left // 3600
        minutes = (left % 3600) // 60
        await message.answer(f"Подарок уже получен. Следующий через {hours} ч {minutes} мин.")
        return
    coins = random.randint(20, 50)
    cat["coins"] += coins
    cat["last_gift"] = now
    gift = random.choice([("Рыбный сюрприз", {"hunger": 15}), ("Тёплый плед", {"energy": 15}), ("Игрушка из коробки", {"mood": 15})])
    name, bonus = gift
    for key, value in bonus.items():
        cat[key] = clamp(cat[key] + value)
    save_cat(cat)
    await reply_with_cat(message, f"🎁 Ежедневный подарок!\n+{coins} 💰 и «{name}»", cat)


@dp.message(F.text == "🎁 Лутбокс")
async def btn_lootbox(message: Message):
    cat = need_cat(message)
    if cat is None:
        await message.answer("Напиши /start, чтобы завести Феню.")
        return
    if cat["coins"] < LOOTBOX_PRICE:
        await message.answer(f"Кото-Сюрприз стоит {LOOTBOX_PRICE} 💰")
        return
    cat["coins"] -= LOOTBOX_PRICE
    code = roll_skin()
    skin = SKINS[code]
    art = html.escape(skin["art"])
    if has_skin(message.from_user.id, code):
        cat["coins"] += DUPLICATE_COINS
        save_cat(cat)
        text = f"🎁 <b>Кото-Сюрприз</b>\nВыпало: {skin['name']} ({skin['rarity']})\n\n<pre>{art}</pre>\nЭтот скин уже есть. Компенсация +{DUPLICATE_COINS} 💰\nБаланс: {cat['coins']} 💰"
    else:
        add_skin(message.from_user.id, code)
        save_cat(cat)
        text = f"🎁 <b>Кото-Сюрприз</b>\nНовый скин: {skin['name']} ({skin['rarity']})\n\n<pre>{art}</pre>\nНадеть можно в /inventory\nБаланс: {cat['coins']} 💰"
    await message.answer(text, parse_mode="HTML", reply_markup=main_keyboard())


@dp.message(Command("inventory"))
async def cmd_inventory(message: Message):
    cat = need_cat(message)
    if cat is None:
        await message.answer("Напиши /start, чтобы завести Феню.")
        return
    owned = list_skins(message.from_user.id)
    equipped = cat.get("equipped_skin") or ""
    if not owned:
        await message.answer("Инвентарь пуст. Открой 🎁 Лутбокс за 30 💰")
        return
    lines = ["🎒 <b>Скины Фени</b>\n"]
    for code in owned:
        skin = SKINS.get(code)
        if not skin:
            continue
        mark = " ← надет" if code == equipped else ""
        lines.append(f"• {skin['name']} ({skin['rarity']}){mark}")
    kb = inventory_keyboard(message.from_user.id, equipped)
    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=kb)


@dp.callback_query(F.data.startswith("eq:"))
async def cb_equip(callback: CallbackQuery):
    cat = load_cat(callback.from_user.id)
    if cat is None:
        await callback.answer("Сначала /start")
        return
    code = callback.data.split(":", 1)[1]
    if code == "off":
        cat["equipped_skin"] = ""
        save_cat(cat)
        await callback.answer("Скин снят")
        await callback.message.answer(status_text(cat), parse_mode="HTML")
        return
    if code not in SKINS or not has_skin(callback.from_user.id, code):
        await callback.answer("Нет такого скина")
        return
    cat["equipped_skin"] = code
    save_cat(cat)
    await callback.answer(f"Надет: {SKINS[code]['name']}")
    await callback.message.answer(status_text(cat), parse_mode="HTML")


@dp.message(Command("gift"))
async def cmd_gift(message: Message, command: CommandObject):
    cat = need_cat(message)
    if cat is None:
        await message.answer("Напиши /start, чтобы завести Феню.")
        return
    args = command.args
    if not args:
        await message.answer("Формат: /gift @username <код_скина>")
        return
    parts = args.split()
    if len(parts) < 2:
        await message.answer("Формат: /gift @username <код_скина>")
        return
    target_username = parts[0].lstrip("@")
    skin_code = find_skin_code(parts[1])
    if skin_code is None:
        await message.answer("Неизвестный скин. Доступные: /inventory")
        return
    if not has_skin(message.from_user.id, skin_code):
        await message.answer("У тебя нет такого скина")
        return
    if message.from_user.username and message.from_user.username.lower() == target_username.lower():
        await message.answer("Нельзя дарить себе")
        return
    if cat.get("equipped_skin") == skin_code:
        cat["equipped_skin"] = ""
        save_cat(cat)
    remove_skin(message.from_user.id, skin_code)
    await message.answer(f"Скин {SKINS[skin_code]['name']} передан игроку @{target_username} (если он есть в игре).")
    await message.answer("⚠️ Автоматическая передача между игроками пока не подключена. Это заглушка.")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "<b>Команды:</b>\n"
        "/start — создать Феню\n"
        "/feed — покормить\n"
        "/play — поиграть\n"
        "/clean — убрать лоток\n"
        "/wash — помыть ковёр\n"
        "/pet — погладить\n"
        "/sleep — уложить спать\n"
        "/status — статус\n"
        "/shop — магазин\n"
        "/casino — казино\n"
        "/achievements — достижения\n"
        "/inventory — инвентарь\n"
        "/top — рейтинг\n"
        "/event — ивент недели\n"
        "/gift — подарить скин (заглушка)"
    )
    await message.answer(text, parse_mode="HTML")


@dp.message()
async def other(message: Message):
    if message.chat.type == "private":
        await message.answer("Нажми кнопку внизу или напиши /start", reply_markup=main_keyboard())


async def decay_loop():
    while True:
        await asyncio.sleep(TICK_SECONDS)
        db = connect_db()
        rows = db.execute("SELECT user_id FROM cats").fetchall()
        db.close()
        for row in rows:
            load_cat(row["user_id"])


async def main():
    init_db()
    asyncio.create_task(decay_loop())
    print("Фенягочи запущен:", datetime.now())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
