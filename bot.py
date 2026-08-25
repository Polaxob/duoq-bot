"""
DuoQ — Основной файл бота
Запуск: python bot.py
"""

import asyncio
import logging
import json
import os
import html as html_mod
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

import database as db

# ── Конфиг ──

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

logging.basicConfig(level=logging.INFO)

# ── Данные игр ──

GAMES = {
    "cs2": {
        "name": "CS2",
        "icon": "🔫",
        "ranks": [
            "Серебро I", "Серебро II", "Серебро III", "Серебро IV", "Серебряная звезда",
            "Серебряная звезда I", "Серебряная звезда II", "Серебряная звезда III",
            "Золотая звезда I", "Золотая звезда II", "Золотая звезда III", "Мастер золотых звёзд",
            "Мастер страж I", "Мастер страж II", "Элита мастеров",
            "Достойный мастер страж", "Орёл-легенда", "Мастер орлов-легенд",
            "Верховный мастер", "Глобальная элита",
        ],
        "roles": ["Стрелок", "Снайпер", "Капитан", "Поддержка", "Прорывной"],
        "platforms": [
            {"name": "FaceIt", "options": ["Уровень 1", "Уровень 2", "Уровень 3", "Уровень 4", "Уровень 5",
                                            "Уровень 6", "Уровень 7", "Уровень 8", "Уровень 9", "Уровень 10"]},
        ],
    },
    "dota2": {
        "name": "Dota 2",
        "icon": "⚔️",
        "ranks": ["Герольд", "Страж", "Крестоносец", "Архонт", "Легенда", "Древний", "Божественный", "Бессмертный"],
        "roles": ["Керри", "Мидлер", "Оффлейнер", "Мягкая поддержка", "Твёрдая поддержка"],
        "platforms": [
            {"name": "DotaBuff (MMR)", "options": []},
        ],
    },
    "valorant": {
        "name": "Valorant",
        "icon": "🛡️",
        "ranks": ["Железо", "Бронза", "Серебро", "Золото", "Платина", "Алмаз", "Восхождение", "Бессмертный", "Радиант"],
        "roles": ["Дуэлянт", "Страж", "Контролёр", "Инициатор"],
        "platforms": [
            {"name": "Трекер статистики", "options": []},
        ],
    },
    "fortnite": {
        "name": "Fortnite",
        "icon": "🏗️",
        "ranks": ["Бот", "Новичок", "Средний", "Выше среднего", "Продвинутый", "Эксперт"],
        "roles": ["Строитель", "Без строительства", "Оба режима"],
        "platforms": [],
    },
    "apex": {
        "name": "Apex Legends",
        "icon": "🔥",
        "ranks": ["Бронза", "Серебро", "Золото", "Платина", "Алмаз", "Мастер", "Хищник"],
        "roles": ["Танк", "Урон", "Поддержка"],
        "platforms": [
            {"name": "Трекер статистики", "options": []},
        ],
    },
    "pubg": {
        "name": "PUBG",
        "icon": "🪖",
        "ranks": ["Бронза", "Серебро", "Золото", "Платина", "Алмаз", "Мастер"],
        "roles": ["Агрессивный", "Пассивный", "Универсал"],
        "platforms": [],
    },
    "rust": {
        "name": "Rust",
        "icon": "🔧",
        "ranks": ["Новичок", "Средний", "Опытный", "Профи"],
        "roles": ["Рейды и PvP", "Строительство", "Сбор ресурсов", "Ролеплей"],
        "platforms": [],
    },
    "minecraft": {
        "name": "Minecraft",
        "icon": "⛏️",
        "ranks": ["Новичок", "Средний", "Опытный", "Профи"],
        "roles": ["Выживание", "Креатив", "Моды", "Арена", "Спидран"],
        "platforms": [
            {"name": "Hypixel", "options": ["Новичок", "Средний", "Опытный", "Профи"]},
        ],
    },
    "gtav": {
        "name": "GTA V",
        "icon": "🚗",
        "ranks": ["Новичок", "Средний", "Опытный", "Профи"],
        "roles": ["Ограбления", "Ролеплей", "Бойцовка", "Фарм денег"],
        "platforms": [],
    },
    "league": {
        "name": "League of Legends",
        "icon": "👑",
        "ranks": ["Железо", "Бронза", "Серебро", "Золото", "Платина", "Алмаз", "Мастер", "Грандмастер", "Челленджер"],
        "roles": ["Топ", "Лес", "Мид", "Стрелок", "Поддержка"],
        "platforms": [
            {"name": "op.gg", "options": []},
        ],
    },
    "rl": {
        "name": "Rocket League",
        "icon": "🏎️",
        "ranks": ["Бронза", "Серебро", "Золото", "Платина", "Алмаз", "Чемпион", "Гранд-чемпион", "Суперзвуковые легенды"],
        "roles": ["На двоих", "На троих", "Один на один"],
        "platforms": [],
    },
    "dayz": {
        "name": "DayZ",
        "icon": "🧟",
        "ranks": ["Новичок", "Средний", "Опытный", "Профи"],
        "roles": ["Выживание и PvP", "Кооп PVE", "Ролеплей"],
        "platforms": [],
    },
}

AGE_GROUPS = ["<16", "16-18", "18-25", "25+"]
GENDER_OPTIONS = {"male": "🧑 Мужской", "female": "👩 Женский", "hidden": "🤔 Не указывать"}
LANGUAGES = {"ru": "🇷🇺 Русский", "en": "🇬🇧 English", "uk": "🇺🇦 Українська", "de": "🇩🇪 Deutsch"}
PLAY_STYLES = ["🔥 Агрессивно", "🧊 Спокойно", "🧠 Стратегически",
               "😂 Развлекаясь", "🏆 Рейтингово", "🎮 Казуально",
               "😤 Соло", "🤝 Командно"]
MIC_OPTIONS = {"mic": "🎤 Микро есть", "listen": "🎧 Только слушаю", "no_mic": "🔇 Нет микрофона"}

# ── Перевод полей extra_fields для отображения ──

EXTRA_FIELD_LABELS = {
    "FaceIt": "🎯FaceIt",
    "prime_status": "Прайм",
    "has_mmr": "MMR",
    "mmr": "MMR",
    "rust_premium": "Премиум",
    "minecraft_premium": "Премиум",
}

# Поля extra_fields, которые не показываем (уже отображаются отдельно)
EXTRA_FIELD_SKIP = {"role", "rank"}


def _format_extra_fields(extra: dict) -> list:
    """Форматировать extra_fields в читаемый список строк."""
    parts = []
    for k, v in extra.items():
        if not v or k in EXTRA_FIELD_SKIP:
            continue
        if k.startswith("platform"):
            parts.append(f"📊 {v}")
        elif k in EXTRA_FIELD_LABELS:
            label = EXTRA_FIELD_LABELS[k]
            parts.append(f"{label}: {v}")
        else:
            parts.append(f"{k}: {v}")
    return parts

# ── Игро-специфичные вопросы (шаг 9/10) ──

GAME_RATING_QUESTIONS = {
    "cs2": [
        {"text": "У тебя есть Прайм статус в CS2?", "field": "prime_status", "type": "yesno"},
    ],
    "dota2": [
        {"text": "У тебя есть рейтинг (MMR) в Dota 2?", "field": "has_mmr", "type": "yesno"},
        {"text": "Укажи свой MMR (число, или «⬅ Пропустить»):", "field": "mmr", "type": "text"},
    ],
    "rust": [
        {"text": "У тебя есть Премиум в Rust?", "field": "rust_premium", "type": "yesno"},
    ],
    "minecraft": [
        {"text": "Премиум (платный) аккаунт Minecraft?", "field": "minecraft_premium", "type": "yesno"},
    ],
}


def _build_rating_queue(selected_games):
    """Построить плоский список вопросов для шага 8."""
    queue = []
    for gk in selected_games:
        qs = GAME_RATING_QUESTIONS.get(gk, [])
        for qi in range(len(qs)):
            queue.append((gk, qi))
    return queue


async def _save_rating_answer(user_id, game_key, field, value):
    """Сохранить ответ в extra_fields конкретной игры."""
    game_name = GAMES[game_key]["name"]
    games = await db.get_user_games(user_id)
    for g in games:
        if g["game_name"] == game_name:
            extra = json.loads(g.get("extra_fields", "{}") or "{}")
            extra[field] = value
            await db.upsert_game_profile(
                user_id, game_name,
                g.get("rank", ""), g.get("role", ""), extra,
            )
            return


async def _show_rating_question(message, queue, q_idx):
    """Показать вопрос из очереди рейтинга."""
    gk, qi = queue[q_idx]
    q = GAME_RATING_QUESTIONS[gk][qi]
    game_name = GAMES[gk]["name"]

    if q["type"] == "yesno":
        kb = [
            [KeyboardButton(text="✅ Есть"), KeyboardButton(text="❌ Нет")],
            [KeyboardButton(text="⬅ Назад")],
        ]
    else:
        kb = [
            [KeyboardButton(text="⬅ Пропустить")],
            [KeyboardButton(text="⬅ Назад")],
        ]

    await message.answer(
        f"{GAMES[gk]['icon']} <b>{game_name}</b>\n\n"
        f"🏆 <b>Шаг 9/10</b> · {q['text']}",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True),
    )

# ── FSM для создания анкеты ──

class Form(StatesGroup):
    nickname = State()
    name = State()
    age = State()
    gender = State()
    games = State()
    game_details = State()
    platform = State()
    play_style = State()
    mic = State()
    rating = State()
    bio = State()
    # Поиск
    search_game = State()
    # Поддержка
    support = State()
    # Настройки
    settings = State()


# ── Клавиатуры ──

def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Создать анкету"), KeyboardButton(text="🔍 Найти тиммейтов")],
            [KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="💬 Поддержка")],
        ],
        resize_keyboard=True,
    )


def back_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅ Назад")]],
        resize_keyboard=True,
    )


# ── /start ──

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await db.get_user(message.from_user.id)
    if not user:
        text = (
            "🎮 <b>Добро пожаловать в DuoQ!</b>\n\n"
            "Найди тиммейтов для любой игры.\n"
            "Создай анкету — бот подберёт тех, кто подходит именно тебе.\n\n"
            "Нажми «📋 Создать анкету» чтобы начать 👇"
        )
    else:
        text = (
            f"🎮 <b>С возвращением, {html_mod.escape(user['nickname'])}!</b>\n\n"
            "Что хочешь сделать?"
        )
    await message.answer(text, reply_markup=main_kb(), parse_mode="HTML")


@router.message(F.text == "📋 Создать анкету")
async def start_form(message: Message, state: FSMContext):
    await state.set_state(Form.nickname)
    await message.answer(
        "📝 <b>Создание анкеты</b>\n\n"
        "<b>Шаг 1/10</b> · Как тебя называют?\n"
        "Никнейм (2–30 символов):",
        parse_mode="HTML",
        reply_markup=back_kb(),
    )


# ── Шаг 1: Ник ──

@router.message(Form.nickname)
async def form_nickname(message: Message, state: FSMContext):
    if message.text == "⬅ Назад":
        await state.clear()
        await message.answer("🏠 В главное меню:", reply_markup=main_kb())
        return
    text = message.text.strip()
    if len(text) < 2 or len(text) > 30:
        await message.answer("❌ Никнейм должен быть от 2 до 30 символов. Попробуй ещё раз:")
        return
    await state.update_data(nickname=text)
    # Переход к шагу 2: Имя
    await state.set_state(Form.name)
    buttons = [[KeyboardButton(text="⬅ Назад")]]
    await message.answer(
        f"✅ Никнейм: <b>{html_mod.escape(text)}</b>\n\n"
        "<b>Шаг 2/10</b> · Какое у тебя имя? (или нажми «⬅ Пропустить»):",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
    )


# ── Шаг 2: Имя ──

@router.message(Form.name)
async def form_name(message: Message, state: FSMContext):
    text = message.text
    if text == "⬅ Назад":
        await state.set_state(Form.nickname)
        await message.answer(
            "📝 <b>Создание анкеты</b>\n\n"
            "<b>Шаг 1/10</b> · Как тебя называют?\n"
            "Никнейм (2–30 символов):",
            parse_mode="HTML",
            reply_markup=back_kb(),
        )
        return
    if text == "⬅ Пропустить":
        name = ""
    else:
        name = text.strip()[:30]
    await state.update_data(name=name)
    # Переход к шагу 3: Возраст
    await state.set_state(Form.age)
    buttons = [[KeyboardButton(text=ag)] for ag in AGE_GROUPS]
    buttons.append([KeyboardButton(text="⬅ Назад")])
    name_display = f"\n✅ Имя: <b>{html_mod.escape(name)}</b>" if name else ""
    await message.answer(
        f"{name_display}\n\n<b>Шаг 3/10</b> · Сколько тебе лет?",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
    )


# ── Шаг 3: Возраст ──

@router.message(Form.age)
async def form_age(message: Message, state: FSMContext):
    if message.text == "⬅ Назад":
        await state.set_state(Form.name)
        buttons = [[KeyboardButton(text="⬅ Назад")]]
        await message.answer(
            "<b>Шаг 2/10</b> · Какое у тебя имя? (или нажми «⬅ Пропустить»):",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
        )
        return
    if message.text not in AGE_GROUPS:
        await message.answer("❌ Выбери возраст кнопкой:")
        return
    await state.update_data(age_group=message.text)
    await state.set_state(Form.gender)
    buttons = [[KeyboardButton(text=v)] for v in GENDER_OPTIONS.values()]
    buttons.append([KeyboardButton(text="⬅ Назад")])
    await message.answer(
        f"✅ Возраст: <b>{html_mod.escape(message.text)}</b>\n\n"
        "<b>Шаг 4/10</b> · Пол:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
    )


# ── Шаг 3: Пол ──

@router.message(Form.gender)
async def form_gender(message: Message, state: FSMContext):
    text = message.text
    if text == "⬅ Назад":
        await state.set_state(Form.age)
        data = await state.get_data()
        buttons = [[KeyboardButton(text=ag)] for ag in AGE_GROUPS]
        buttons.append([KeyboardButton(text="⬅ Назад")])
        await message.answer(
            "Назад к выбору возраста:",
            reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
        )
        return
    if text not in GENDER_OPTIONS.values():
        await message.answer("❌ Выбери пол кнопкой:")
        return
    gender = [k for k, v in GENDER_OPTIONS.items() if v == text][0]
    await state.update_data(gender=gender)

    # Создаём пользователя в БД (nickname + name + age_group + gender собраны)
    data = await state.get_data()
    await db.create_user(
        message.from_user.id,
        nickname=data["nickname"],
        name=data.get("name", ""),
        age_group=data["age_group"],
        gender=gender,
    )

    await state.set_state(Form.games)
    kb = []
    for i in range(0, len(GAMES), 2):
        row = []
        for gk in list(GAMES.keys())[i:i+2]:
            row.append(KeyboardButton(text=f"{GAMES[gk]['icon']} {GAMES[gk]['name']}"))
        kb.append(row)
    kb.append([KeyboardButton(text="✅ Готово")])
    kb.append([KeyboardButton(text="⬅ Назад")])
    await message.answer(
        "🎮 <b>Шаг 5/10</b> · Во что играешь?\n\n"
        "Нажимай на игры, потом нажми «✅ Готово»:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True),
    )
    await state.update_data(selected_games=[])


@router.message(Form.games)
async def form_games(message: Message, state: FSMContext):
    text = message.text
    data = await state.get_data()
    selected = data.get("selected_games", [])

    if text == "⬅ Назад":
        await state.set_state(Form.gender)
        buttons = [[KeyboardButton(text=v)] for v in GENDER_OPTIONS.values()]
        buttons.append([KeyboardButton(text="⬅ Назад")])
        await message.answer("Назад к выбору пола:", reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
        return

    if text == "✅ Готово":
        if not selected:
            await message.answer("❌ Выбери хотя бы одну игру!")
            return
        # Переходим к деталям по первой игре
        await state.update_data(current_game_idx=0, game_details={})
        first_game = selected[0]
        game_data = GAMES[first_game]
        buttons = [[KeyboardButton(text=r)] for r in game_data["roles"]]
        buttons.append([KeyboardButton(text="⬅ Назад")])
        await state.set_state(Form.game_details)
        await message.answer(
            f"🎯 <b>Шаг 6/10</b> · Детали по <b>{game_data['name']}</b>\n\n"
            "Выбери свою роль:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
        )
        await state.update_data(current_detail_field="role", current_game_key=first_game)
        return

    # Toggle game selection — strip "✅ " prefix if present
    clean_text = text.lstrip("✅ ")
    game_key = None
    for k, v in GAMES.items():
        if clean_text == f"{v['icon']} {v['name']}":
            game_key = k
            break

    if game_key is None:
        await message.answer("❌ Нажми на игру или «✅ Готово»:")
        return

    if game_key in selected:
        selected.remove(game_key)
    else:
        selected.append(game_key)

    await state.update_data(selected_games=selected)

    # Rebuild keyboard with toggles
    kb = []
    for i in range(0, len(GAMES), 2):
        row = []
        for gk in list(GAMES.keys())[i:i+2]:
            prefix = "✅ " if gk in selected else ""
            row.append(KeyboardButton(text=f"{prefix}{GAMES[gk]['icon']} {GAMES[gk]['name']}"))
        kb.append(row)
    kb.append([KeyboardButton(text="✅ Готово")])
    kb.append([KeyboardButton(text="⬅ Назад")])

    count = len(selected)
    await message.answer(
        f"Выбрано: <b>{count}</b> игр",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True),
    )


# ── Шаг 5: Детали по играм (роль + ранг) ──

@router.message(Form.game_details)
async def form_game_details(message: Message, state: FSMContext):
    text = message.text
    data = await state.get_data()

    if text == "⬅ Назад":
        await state.set_state(Form.games)
        kb = []
        selected = data.get("selected_games", [])
        for i in range(0, len(GAMES), 2):
            row = []
            for gk in list(GAMES.keys())[i:i+2]:
                prefix = "✅ " if gk in selected else ""
                row.append(KeyboardButton(text=f"{prefix}{GAMES[gk]['icon']} {GAMES[gk]['name']}"))
            kb.append(row)
        kb.append([KeyboardButton(text="✅ Готово")])
        await message.answer("Назад к выбору игр:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        return

    field = data.get("current_detail_field")
    game_key = data.get("current_game_key")
    game_data = GAMES[game_key]
    details = data.get("game_details", {})
    if game_key not in details:
        details[game_key] = {}

    if field == "role":
        if text not in game_data["roles"]:
            await message.answer("❌ Выбери роль кнопкой:")
            return
        details[game_key]["role"] = text
        await state.update_data(game_details=details, current_detail_field="rank")

        buttons = [[KeyboardButton(text=r)] for r in game_data["ranks"]]
        buttons.append([KeyboardButton(text="🚫 Нет ранга")])
        buttons.append([KeyboardButton(text="⬅ Назад")])
        await message.answer(
            f"✅ Роль: <b>{text}</b>\n\n"
            "Выбери свой ранг:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
        )
        return

    if field == "rank":
        if text not in game_data["ranks"] and text != "🚫 Нет ранга":
            await message.answer("❌ Выбери ранг кнопкой:")
            return
        details[game_key]["rank"] = "" if text == "🚫 Нет ранга" else text
        await state.update_data(game_details=details)

        # Проверяем, есть ли платформы у игры
        platforms = game_data.get("platforms", [])
        if platforms:
            # Есть платформы — показываем выбор
            await state.set_state(Form.platform)
            await state.update_data(current_detail_field="platform", current_platform_idx=0)
            platform = platforms[0]
            buttons = []
            if platform["options"]:
                buttons = [[KeyboardButton(text=o)] for o in platform["options"]]
                buttons.append([KeyboardButton(text="🚫 Нет")])
                buttons.append([KeyboardButton(text="⬅ Пропустить")])
            else:
                buttons.append([KeyboardButton(text="🚫 Нет")])
                buttons.append([KeyboardButton(text="⬅ Пропустить")])
            await message.answer(
                f"✅ Ранг: <b>{text}</b>\n\n"
                f"📊 Укажи свой <b>{platform['name']}</b> (или нажми «⬅ Пропустить»):",
                parse_mode="HTML",
                reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
            )
        else:
            # Нет платформ — сохраняем сразу
            await _save_game_and_advance(message, state, data, details, game_key)
        return


# ── Сохранение игры и переход к следующей ──

async def _save_game_and_advance(message, state, data, details, game_key):
    game_data = GAMES[game_key]
    extra = details[game_key]
    platform_value = extra.pop("platform_value", "")
    platform_name = extra.pop("platform_name", "")
    if platform_name and platform_value:
        extra[platform_name] = platform_value

    await db.upsert_game_profile(
        message.from_user.id, game_data["name"], extra.get("rank", ""),
        extra.get("role", ""), extra
    )

    selected = data.get("selected_games", [])
    idx = data.get("current_game_idx", 0) + 1

    if idx < len(selected):
        next_game = selected[idx]
        next_data = GAMES[next_game]
        await state.set_state(Form.game_details)
        await state.update_data(current_game_idx=idx, current_game_key=next_game, current_detail_field="role")
        buttons = [[KeyboardButton(text=r)] for r in next_data["roles"]]
        buttons.append([KeyboardButton(text="⬅ Назад")])
        await message.answer(
            f"✅ Сохранено!\n\n"
            f"🎯 Теперь <b>{next_data['name']}</b>\n"
            "Выбери свою роль:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
        )
    else:
        # Все игры пройдены — стиль игры
        await state.set_state(Form.play_style)
        await state.update_data(selected_styles=[])
        buttons = [[KeyboardButton(text=s)] for s in PLAY_STYLES]
        buttons.append([KeyboardButton(text="✅ Далее")])
        buttons.append([KeyboardButton(text="⬅ Назад")])
        await message.answer(
            "🔥 <b>Шаг 7/10</b> · Как ты играешь?\n\n"
            "Выбери до 3 стилей, потом «✅ Далее»:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
        )


# ── Шаг 5b: Платформа (FaceIt и т.д.) ──

@router.message(Form.platform)
async def form_platform(message: Message, state: FSMContext):
    text = message.text
    data = await state.get_data()
    game_key = data.get("current_game_key")
    game_data = GAMES[game_key]
    platforms = game_data.get("platforms", [])
    platform_idx = data.get("current_platform_idx", 0)
    details = data.get("game_details", {})

    if text == "⬅ Назад":
        # Назад к выбору ранга
        await state.set_state(Form.game_details)
        await state.update_data(current_detail_field="rank")
        buttons = [[KeyboardButton(text=r)] for r in game_data["ranks"]]
        buttons.append([KeyboardButton(text="🚫 Нет ранга")])
        buttons.append([KeyboardButton(text="⬅ Назад")])
        await message.answer("Назад к выбору ранга:", reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
        return

    platform = platforms[platform_idx]

    if text == "⬅ Пропустить" or text == "🚫 Нет":
        # Пропускаем эту платформу
        pass
    else:
        if platform["options"] and text not in platform["options"]:
            await message.answer("❌ Выбери кнопкой или нажми «⬅ Пропустить»:")
            return
        details[game_key][f"platform_{platform_idx}"] = text

    # Следующая платформа или сохраняем
    next_idx = platform_idx + 1
    if next_idx < len(platforms):
        await state.update_data(current_platform_idx=next_idx)
        next_platform = platforms[next_idx]
        buttons = []
        if next_platform["options"]:
            buttons = [[KeyboardButton(text=o)] for o in next_platform["options"]]
            buttons.append([KeyboardButton(text="🚫 Нет")])
        buttons.append([KeyboardButton(text="⬅ Пропустить")])
        buttons.append([KeyboardButton(text="⬅ Назад")])
        await message.answer(
            f"📊 Укажи свой <b>{next_platform['name']}</b> (или «⬅ Пропустить»):",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
        )
    else:
        # Все платформы пройдены — собираем extra и сохраняем
        for i, p in enumerate(platforms):
            key = f"platform_{i}"
            if key in details[game_key]:
                details[game_key]["platform_value"] = details[game_key].pop(key)
                details[game_key]["platform_name"] = p["name"]
        await state.update_data(game_details=details)
        await state.set_state(Form.game_details)
        await _save_game_and_advance(message, state, data, details, game_key)


# ── Шаг 6: Стиль игры ──

@router.message(Form.play_style)
async def form_play_style(message: Message, state: FSMContext):
    text = message.text
    data = await state.get_data()

    if text == "⬅ Назад":
        # Назад к деталям последней игры
        selected = data.get("selected_games", [])
        idx = max(0, data.get("current_game_idx", 0))
        if idx < len(selected):
            game_key = selected[idx]
            game_data = GAMES[game_key]
            await state.set_state(Form.game_details)
            await state.update_data(current_detail_field="role", current_game_key=game_key)
            buttons = [[KeyboardButton(text=r)] for r in game_data["roles"]]
            buttons.append([KeyboardButton(text="⬅ Назад")])
            await message.answer("Назад к деталям игры:", reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
        return

    if text == "✅ Далее":
        styles = data.get("selected_styles", [])
        if not styles:
            await message.answer("❌ Выбери хотя бы один стиль!")
            return
        await db.update_user(message.from_user.id, play_style=json.dumps(styles))
        # Шаг 7: Микро и язык
        await state.set_state(Form.mic)
        buttons = [[KeyboardButton(text=v)] for v in MIC_OPTIONS.values()]
        buttons.append([KeyboardButton(text="⬅ Назад")])
        await message.answer(
            "🎤 <b>Шаг 8/10</b> · Готов voice-чатить?\n\n"
            "Выбери вариант:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
        )
        return

    # Toggle style — strip "✅ " prefix if present
    clean_text = text.lstrip("✅ ")
    styles = data.get("selected_styles", [])
    if clean_text in styles:
        styles.remove(clean_text)
    elif len(styles) < 3:
        styles.append(clean_text)
    else:
        await message.answer("❌ Максимум 3 стиля!")
        return

    await state.update_data(selected_styles=styles)

    kb = []
    for s in PLAY_STYLES:
        prefix = "✅ " if s in styles else ""
        kb.append([KeyboardButton(text=f"{prefix}{s}")])
    kb.append([KeyboardButton(text="✅ Далее")])
    kb.append([KeyboardButton(text="⬅ Назад")])
    await message.answer(
        f"Выбрано: <b>{len(styles)}/3</b>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True),
    )


# ── Шаг 7: Микрофон ──

@router.message(Form.mic)
async def form_mic(message: Message, state: FSMContext):
    text = message.text

    if text == "⬅ Назад":
        await state.set_state(Form.play_style)
        await state.update_data(selected_styles=[])
        buttons = [[KeyboardButton(text=s)] for s in PLAY_STYLES]
        buttons.append([KeyboardButton(text="✅ Далее")])
        buttons.append([KeyboardButton(text="⬅ Назад")])
        await message.answer("Назад к стилям игры:", reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
        return

    if text not in MIC_OPTIONS.values():
        await message.answer("❌ Выбери вариант кнопкой:")
        return

    mic = [k for k, v in MIC_OPTIONS.items() if v == text][0]
    await db.update_user(message.from_user.id, mic_status=mic)

    # Шаг 8: Игро-специфичные вопросы о рейтинге/премиуме
    data = await state.get_data()
    queue = _build_rating_queue(data.get("selected_games", []))
    await state.update_data(rating_queue=queue, rating_q_idx=0)

    if queue:
        await state.set_state(Form.rating)
        await _show_rating_question(message, queue, 0)
    else:
        # Нет вопросов — сразу к био
        await state.set_state(Form.bio)
        await message.answer(
            f"✅ Микро: <b>{text}</b>\n\n"
            "📝 <b>Шаг 10/10</b> · Расскажи о себе (необязательно):\n\n"
            "Чего ищешь в тиммейтах? Любимые мемы?\n"
            "Или нажми «✅ Сохранить» чтобы пропустить:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="✅ Сохранить")],
                    [KeyboardButton(text="⬅ Назад")],
                ],
                resize_keyboard=True,
            ),
        )


# ── Шаг 8: Игро-специфичные вопросы о рейтинге/премиуме ──

@router.message(Form.rating)
async def form_rating(message: Message, state: FSMContext):
    text = message.text
    data = await state.get_data()
    queue = data.get("rating_queue", [])
    idx = data.get("rating_q_idx", 0)

    if text == "⬅ Назад":
        if idx > 0:
            idx -= 1
            await state.update_data(rating_q_idx=idx)
            await _show_rating_question(message, queue, idx)
        else:
            # Назад к микрофону
            await state.set_state(Form.mic)
            buttons = [[KeyboardButton(text=v)] for v in MIC_OPTIONS.values()]
            buttons.append([KeyboardButton(text="⬅ Назад")])
            await message.answer(
                "Назад к микрофону:",
                reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
            )
        return

    # Сохраняем ответ на текущий вопрос
    gk, qi = queue[idx]
    q = GAME_RATING_QUESTIONS[gk][qi]
    field = q["field"]

    if text == "⬅ Пропустить":
        value = ""
    elif text == "✅ Есть":
        value = "Есть"
    elif text == "❌ Нет":
        value = "Нет"
    else:
        value = text[:100]

    await _save_rating_answer(message.from_user.id, gk, field, value)

    # Следующий вопрос или завершение
    idx += 1
    if idx < len(queue):
        await state.update_data(rating_q_idx=idx)
        await _show_rating_question(message, queue, idx)
    else:
        # Все вопросы пройдены → био
        await state.set_state(Form.bio)
        await message.answer(
            "✅ Рейтинг / статус сохранён!\n\n"
            "📝 <b>Шаг 10/10</b> · Расскажи о себе (необязательно):\n\n"
            "Чего ищешь в тиммейтах? Любимые мемы?\n"
            "Или нажми «✅ Сохранить» чтобы пропустить:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="✅ Сохранить")],
                    [KeyboardButton(text="⬅ Назад")],
                ],
                resize_keyboard=True,
            ),
        )


# ── Шаг 10: О себе ──

@router.message(Form.bio)
async def form_bio(message: Message, state: FSMContext):
    text = message.text

    if text == "⬅ Назад":
        data = await state.get_data()
        queue = data.get("rating_queue", [])
        if queue:
            last_idx = len(queue) - 1
            await state.set_state(Form.rating)
            await state.update_data(rating_q_idx=last_idx)
            await _show_rating_question(message, queue, last_idx)
        else:
            await state.set_state(Form.mic)
            buttons = [[KeyboardButton(text=v)] for v in MIC_OPTIONS.values()]
            buttons.append([KeyboardButton(text="⬅ Назад")])
            await message.answer(
                "Назад к микрофону:",
                reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
            )
        return

    bio = "" if text == "✅ Сохранить" else text[:500]
    await db.update_user(message.from_user.id, bio=bio)

    # Завершение анкеты
    user = await db.get_user(message.from_user.id)
    games = await db.get_user_games(message.from_user.id)
    await state.clear()

    games_lines = []
    for g in games:
        extra = json.loads(g.get("extra_fields", "{}") or "{}")
        extra_parts = _format_extra_fields(extra)
        # Найти иконку игры
        game_icon = "🎮"
        for gk, gd in GAMES.items():
            if gd["name"] == g["game_name"]:
                game_icon = gd["icon"]
                break
        role_str = f" · {g['role']}" if g.get("role") else ""
        extra_str = " · ".join(extra_parts)
        line = f"{game_icon} {g['game_name']} · {g['rank']}{role_str}"
        if extra_str:
            line += f"\n{extra_str}"
        games_lines.append(line)
    games_text = "\n".join(games_lines) if games_lines else "не указано"
    gender_text = GENDER_OPTIONS.get(user.get("gender", "hidden"), "🤔 Не указывать")
    mic_text = MIC_OPTIONS.get(user.get("mic_status", "no_mic"), "🔇 Нет микрофона")

    await message.answer(
        f"🎉 <b>Анкета готова!</b>\n\n"
        f"🎮 <b>{html_mod.escape(user['nickname'])}</b>"
        f"{(' · ' + html_mod.escape(user['name'])) if user.get('name') else ''}\n"
        f"📅 {user['age_group']} · {gender_text}\n"
        f"🎯 {games_text}\n"
        f"{mic_text}\n"
        f"💬 {user.get('bio', '')[:100] or 'не указано'}\n\n"
        "Теперь нажми «🔍 Найти тиммейтов» чтобы найти напарников!",
        parse_mode="HTML",
        reply_markup=main_kb(),
    )


# ── Найти тиммейтов ──

@router.message(F.text == "🔍 Найти тиммейтов")
async def search_start(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Сначала создай анкету! Нажми «📋 Создать анкету»")
        return

    games = await db.get_user_games(message.from_user.id)
    if not games:
        await message.answer("❌ Сначала добавь игры в анкету!")
        return

    kb = [[KeyboardButton(text=f"🎯 {g['game_name']}")] for g in games]
    kb.append([KeyboardButton(text="🎯 Все мои игры")])
    kb.append([KeyboardButton(text="⬅ В меню")])

    await state.set_state(Form.search_game)
    await message.answer(
        "🔍 <b>Поиск тиммейтов</b>\n\n"
        "Какую игру ищешь?",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True),
    )


@router.message(Form.search_game)
async def search_select_game(message: Message, state: FSMContext):
    text = message.text

    if text == "⬅ В меню":
        await state.clear()
        await message.answer("🏠 В главное меню:", reply_markup=main_kb())
        return

    game_filter = None
    if text == "🎯 Все мои игры":
        game_filter = None
    else:
        game_name = text.replace("🎯 ", "")
        game_filter = game_name

    await state.clear()

    # Получаем кандидатов
    seen = await db.get_seen_ids(message.from_user.id)
    profiles = await db.get_active_profiles(message.from_user.id, game_filter)

    # Фильтруем уже просмотренных
    candidates = [p for p in profiles if p["telegram_id"] not in seen]

    if not candidates:
        await message.answer(
            "😔 Пока нет новых анкет для просмотра.\n"
            "Попробуй позже или выбери другую игру!",
            reply_markup=main_kb(),
        )
        return

    # Сохраняем очередь в state (или в память)
    await state.set_state(Form.search_game)
    await state.update_data(candidates=[c["telegram_id"] for c in candidates], current_idx=0)

    # Показываем первую карточку
    await show_card(message, state, candidates[0]["telegram_id"], message.from_user.id)


async def show_card(message_or_cb, state, candidate_id: int, viewer_id: int):
    user = await db.get_user(candidate_id)
    if not user:
        if isinstance(message_or_cb, Message):
            await message_or_cb.answer("Анкета больше не активна.")
        return

    games = await db.get_user_games(candidate_id)
    gender_text = GENDER_OPTIONS.get(user.get("gender", "hidden"), "")
    mic_text = MIC_OPTIONS.get(user.get("mic_status", "no_mic"), "")

    games_lines = []
    for g in games:
        # Найти иконку игры
        game_icon = "🎮"
        for gk, gd in GAMES.items():
            if gd["name"] == g["game_name"]:
                game_icon = gd["icon"]
                break
        role_str = f" · {g['role']}" if g.get("role") else ""
        extra = json.loads(g.get("extra_fields", "{}") or "{}")
        extra_parts = _format_extra_fields(extra)
        lines = f"  {game_icon} {g['game_name']} · {g['rank']}{role_str}"
        if extra_parts:
            lines += "\n" + " · ".join(extra_parts)
        games_lines.append(lines)
    games_text = "\n".join(games_lines) if games_lines else "  не указано"

    bio_text = user.get("bio", "")
    bio_section = f"\n💬 <i>\"{bio_text[:200]}\"</i>" if bio_text else ""

    card = (
        f"🎮 <b>{html_mod.escape(user['nickname'])}</b>"
        f"{(' · ' + html_mod.escape(user['name'])) if user.get('name') else ''}\n"
        f"📅 {user['age_group']} · {gender_text}\n\n"
        f"{games_text}\n"
        f"{mic_text}{bio_section}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👎 Пропустить", callback_data=f"skip:{candidate_id}"),
            InlineKeyboardButton(text="💬 Написать", callback_data=f"like:{candidate_id}"),
        ],
        [
            InlineKeyboardButton(text="⭐ В избранное", callback_data=f"fav:{candidate_id}"),
            InlineKeyboardButton(text="⚠️ Пожаловаться", callback_data=f"report:{candidate_id}"),
        ],
    ])

    if isinstance(message_or_cb, CallbackQuery):
        await message_or_cb.message.answer(card, reply_markup=kb, parse_mode="HTML")
    else:
        await message_or_cb.answer(card, reply_markup=kb, parse_mode="HTML")


# ── Inline кнопки действий ──

@router.callback_query(F.data.startswith("like:"))
async def cb_like(callback: CallbackQuery, state: FSMContext):
    target_id = int(callback.data.split(":")[1])
    viewer_id = callback.from_user.id

    await db.save_action(viewer_id, target_id, "like")
    await callback.answer("💬 Запрос отправлен! Если он тоже захочет — будет матч! 🎉")

    # Проверяем взаимность
    mutual = await db.check_mutual_like(viewer_id, target_id)
    if mutual:
        await db.create_match(viewer_id, target_id)
        target = await db.get_user(target_id)
        name = target["nickname"] if target else "Игрок"
        await callback.message.answer(
            f"🎉 <b>МАТЧ!</b>\n\n"
             f"Вы и <b>{html_mod.escape(name)}</b> оба хотят играть вместе!\n"
            f"Напиши ему первым 👇",
            parse_mode="HTML",
        )

    # Следующая карточка
    data = await state.get_data()
    candidates = data.get("candidates", [])
    idx = data.get("current_idx", 0) + 1
    if idx < len(candidates):
        await state.update_data(current_idx=idx)
        await show_card(callback, state, candidates[idx], viewer_id)
    else:
        await callback.message.answer("🔍 Анкеты закончились! Возвращайся позже 🎮", reply_markup=main_kb())


@router.callback_query(F.data.startswith("skip:"))
async def cb_skip(callback: CallbackQuery, state: FSMContext):
    target_id = int(callback.data.split(":")[1])
    viewer_id = callback.from_user.id

    await db.save_action(viewer_id, target_id, "skip")
    await callback.answer("Пропущено")

    data = await state.get_data()
    candidates = data.get("candidates", [])
    idx = data.get("current_idx", 0) + 1
    if idx < len(candidates):
        await state.update_data(current_idx=idx)
        await show_card(callback, state, candidates[idx], viewer_id)
    else:
        await callback.message.answer("🔍 Анкеты закончились!", reply_markup=main_kb())


@router.callback_query(F.data.startswith("fav:"))
async def cb_fav(callback: CallbackQuery, state: FSMContext):
    target_id = int(callback.data.split(":")[1])
    viewer_id = callback.from_user.id

    await db.save_action(viewer_id, target_id, "fav")
    await callback.answer("⭐ Добавлено в избранное!")

    mutual = await db.check_mutual_like(viewer_id, target_id)
    if mutual:
        await db.create_match(viewer_id, target_id)
        target = await db.get_user(target_id)
        name = target["nickname"] if target else "Игрок"
        await callback.message.answer(
            f"🎉 <b>МАТЧ!</b>\n\n"
             f"Вы и <b>{html_mod.escape(name)}</b> оба хотят играть вместе!\n"
            f"Напиши ему первым 👇",
            parse_mode="HTML",
        )

    data = await state.get_data()
    candidates = data.get("candidates", [])
    idx = data.get("current_idx", 0) + 1
    if idx < len(candidates):
        await state.update_data(current_idx=idx)
        await show_card(callback, state, candidates[idx], viewer_id)
    else:
        await callback.message.answer("🔍 Анкеты закончились!", reply_markup=main_kb())


@router.callback_query(F.data.startswith("report:"))
async def cb_report(callback: CallbackQuery):
    target_id = int(callback.data.split(":")[1])
    db_conn = await db.get_db()
    await db_conn.execute(
        "INSERT INTO reports (reporter_id, reported_id, reason) VALUES (?, ?, ?)",
        (callback.from_user.id, target_id, "user_report"),
    )
    await db_conn.commit()
    await db_conn.close()
    await callback.answer("⚠️ Жалоба отправлена. Спасибо!")


# ── Мой профиль ──

@router.message(F.text == "👤 Мой профиль")
async def my_profile(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ У тебя ещё нет анкеты. Нажми «📋 Создать анкету»")
        return

    games = await db.get_user_games(message.from_user.id)
    matches = await db.get_matches(message.from_user.id)
    favorites = await db.get_user_favorites(message.from_user.id)

    gender_text = GENDER_OPTIONS.get(user.get("gender", "hidden"), "")
    mic_text = MIC_OPTIONS.get(user.get("mic_status", "no_mic"), "")
    games_lines = []
    for g in games:
        extra = json.loads(g.get("extra_fields", "{}") or "{}")
        extra_parts = _format_extra_fields(extra)
        # Найти иконку игры
        game_icon = "🎮"
        for gk, gd in GAMES.items():
            if gd["name"] == g["game_name"]:
                game_icon = gd["icon"]
                break
        role_str = f" · {g['role']}" if g.get("role") else ""
        extra_str = " · ".join(extra_parts)
        line = f"{game_icon} {g['game_name']} · {g['rank']}{role_str}"
        if extra_str:
            line += f"\n{extra_str}"
        games_lines.append(line)
    games_text = "\n".join(games_lines) if games_lines else "не указано"

    text = (
        f"👤 <b>Мой профиль</b>\n\n"
        f"🎮 <b>{html_mod.escape(user['nickname'])}</b>"
        f"{(' · ' + html_mod.escape(user['name'])) if user.get('name') else ''}\n"
        f"📅 {user['age_group']} · {gender_text}\n"
        f"🎯 {games_text}\n"
        f"{mic_text}\n"
        f"💬 {user.get('bio', '')[:100] or 'не указано'}\n\n"
        f"📊 Статистика:\n"
        f"  🎉 Матчей: <b>{len(matches)}</b>\n"
        f"  ⭐ В избранном у: <b>{len(favorites)}</b>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_profile")],
        [InlineKeyboardButton(text="🎮 Мои матчи", callback_data="my_matches")],
    ])

    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "my_matches")
async def cb_my_matches(callback: CallbackQuery):
    matches = await db.get_matches(callback.from_user.id)
    if not matches:
        await callback.message.answer("😔 Пока нет матчей. Продолжай искать! 🔍")
        await callback.answer()
        return

    text = "🎉 <b>Мои матчи:</b>\n\n"
    for m in matches:
        other_id = m["user_b_id"] if m["user_a_id"] == callback.from_user.id else m["user_a_id"]
        other = await db.get_user(other_id)
        if other:
            text += f"🎮 {other['nickname']}\n"

    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


# ── Поддержка ──

@router.message(F.text == "💬 Поддержка")
async def support_start(message: Message, state: FSMContext):
    await state.set_state(Form.support)
    await message.answer(
        "💬 <b>Поддержка</b>\n\n"
        "Напиши своё сообщение, и оно будет анонимно переслано разработчику.\n"
        "Ответ придёт тебе в бот.\n\n"
        "Напиши сообщение или нажми «⬅ Назад»:",
        parse_mode="HTML",
        reply_markup=back_kb(),
    )


@router.message(Form.support)
async def support_send(message: Message, state: FSMContext):
    text = message.text

    if text == "⬅ Назад":
        await state.clear()
        await message.answer("🏠 В главное меню:", reply_markup=main_kb())
        return

    if not text or len(text) < 2:
        await message.answer("❌ Напиши сообщение длиннее 2 символов:")
        return

    # Анонимная пересылка владельцу
    if OWNER_ID:
        try:
            await bot.send_message(
                OWNER_ID,
                f"📩 <b>Анонимное сообщение из бота DuoQ</b>\n"
                f"👤 User ID: <code>{message.from_user.id}</code>\n"
                f"🆔 Никнейм: @{message.from_user.username or 'нет'}\n\n"
                f"{html_mod.escape(text[:1000])}\n\n"
                f"💬 Ответить: /reply {message.from_user.id} <текст>",
                parse_mode="HTML",
            )
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение владельцу: {e}")

    await state.clear()
    await message.answer(
        "✅ <b>Сообщение отправлено!</b>\n\n"
        "Разработчик получит его анонимно.",
        parse_mode="HTML",
        reply_markup=main_kb(),
    )


@router.message(Command("reply"))
async def cmd_reply(message: Message):
    """Команда для владельца: /reply USER_ID текст"""
    if OWNER_ID and message.from_user.id != OWNER_ID:
        await message.answer("❌ У тебя нет прав.")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Использование: /reply USER_ID текст")
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("USER_ID должен быть числом.")
        return

    reply_text = parts[2]
    try:
        await bot.send_message(
            target_id,
            f"💬 <b>Ответ от поддержки DuoQ:</b>\n\n{html_mod.escape(reply_text[:1000])}",
            parse_mode="HTML",
        )
        await message.answer(f"✅ Ответ отправлен пользователю {target_id}")
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить: {e}")


# ── Настройки ──

@router.message(F.text == "⚙️ Настройки")
async def settings(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить анкету", callback_data="delete_profile")],
        [InlineKeyboardButton(text="📋 Правила", callback_data="rules")],
    ])
    await message.answer("⚙️ <b>Настройки</b>\n\nВыбери действие:", reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "delete_profile")
async def cb_delete_profile(callback: CallbackQuery):
    db_conn = await db.get_db()
    await db_conn.execute("DELETE FROM game_profiles WHERE user_id = ?", (callback.from_user.id,))
    await db_conn.execute("DELETE FROM users WHERE telegram_id = ?", (callback.from_user.id,))
    await db_conn.commit()
    await db_conn.close()
    await callback.message.answer("🗑 Анкета удалена. Возвращайся, когда захочешь снова! 👋", reply_markup=main_kb())
    await callback.answer()


@router.callback_query(F.data == "rules")
async def cb_rules(callback: CallbackQuery):
    text = (
        "📋 <b>Правила DuoQ:</b>\n\n"
        "1. Будь вежлив с тиммейтами\n"
        "2. Не создавай фейковые анкеты\n"
        "3. Не спами в личных сообщениях\n"
        "4. Не спамь в поиске\n\n"
        "Пользуйтесь ботом с удовольствием — мы всё делаем для вас! 🤝"
    )
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


# ── Пропуск шага ──

@router.message(F.text == "⬅ Назад")
async def go_back_any(message: Message, state: FSMContext):
    current = await state.get_state()
    if current is None:
        await message.answer("🏠 В главное меню:", reply_markup=main_kb())


# ── Запуск ──

async def main():
    await db.init_db()
    logging.info("DuoQ Bot запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
