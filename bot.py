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
        "ranks": ["Титан", "Божество", "Властелин", "Легенда", "Герой", "Рыцарь", "Страж", "Рекрут"],
        "roles": ["Керри", "Мидлер", "Оффлейнер", "Мягкая поддержка", "Твёрдая поддержка"],
        "platforms": [],
    },
    "fortnite": {
        "name": "Fortnite",
        "icon": "🏗️",
        "ranks": ["Бронза", "Серебро", "Золото", "Платина", "Бриллиант", "Элита", "Чемпион", "Нереальный"],
        "roles": ["Строитель", "Без строительства", "Оба режима"],
        "platforms": [],
    },
    "pubg": {
        "name": "PUBG Mobile",
        "icon": "🪖",
        "ranks": ["Бронза", "Серебро", "Золото", "Платина", "Алмаз", "Корона", "Ас", "Ас-Мастер", "Ас-Доминатор", "Завоеватель"],
        "roles": ["Агрессивный", "Пассивный", "Универсал"],
        "platforms": [],
    },
    "rust": {
        "name": "Rust",
        "icon": "🔧",
        "ranks": ["Новичок", "Средний", "Опытный", "Профи"],
        "roles": ["Рейды и PvP", "Строительство", "Сбор ресурсов", "Электрик", "✏️ Написать свою"],
        "platforms": [],
    },
    "minecraft": {
        "name": "Minecraft",
        "icon": "⛏️",
        "ranks": ["Новичок", "Средний", "Опытный", "Профи"],
        "roles": ["Выживание", "Креатив", "Моды", "Арена", "Спидран"],
        "platforms": [
            {"name": "Лицензия Minecraft", "options": ["Есть", "Нет"], "question": "🏆 Есть ли у тебя лицензия Minecraft?"},
        ],
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
    "mmr": "MMR",
    "rust_premium": "Премиум",
    "metro_royale": "Metro Royale",
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


# ── Игро-специфичные вопросы (внутри деталей каждой игры) ──

GAME_RATING_QUESTIONS = {
    "cs2": [
        {"text": "У тебя есть Прайм статус в CS2?", "field": "prime_status", "type": "yesno"},
    ],
    "dota2": [
        {"text": "Укажи свой MMR (число, или «➡ Пропустить»):", "field": "mmr", "type": "text"},
    ],
    "rust": [
        {"text": "У тебя есть Премиум в Rust?", "field": "rust_premium", "type": "yesno"},
    ],
    "pubg": [
        {"text": "🕌 Ты играешь в <b>Metro Royale</b>?", "field": "metro_royale", "type": "yesno"},
    ],
}


def _has_rating_questions(game_key: str) -> bool:
    """Проверить, есть ли вопросы для конкретной игры."""
    return bool(GAME_RATING_QUESTIONS.get(game_key))


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


async def _show_game_rating_question(message, game_key, q_idx):
    """Показать вопрос из рейтинга конкретной игры."""
    qs = GAME_RATING_QUESTIONS[game_key]
    q = qs[q_idx]
    game_name = GAMES[game_key]["name"]

    if q["type"] == "yesno":
        kb = [
            [KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")],
            [KeyboardButton(text="➡ Пропустить")],
            [KeyboardButton(text="⬅ Назад")],
        ]
    else:
        kb = [
            [KeyboardButton(text="🚫 Нет")],
            [KeyboardButton(text="➡ Пропустить")],
            [KeyboardButton(text="⬅ Назад")],
        ]

    await message.answer(
        f"{GAMES[game_key]['icon']} <b>{game_name}</b>\n\n"
        f"{q['text']}",
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
    game_rating = State()  # вопросы рейтинга внутри деталей игры
    play_style = State()
    custom_style = State()  # ввод своего стиля
    mic = State()
    bio = State()
    # Поиск
    search_game = State()
    # Редактирование
    edit = State()
    edit_text = State()
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


def _edit_menu_kb():
    """Клавиатура меню редактирования профиля."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Никнейм", callback_data="edit_field:nickname"),
         InlineKeyboardButton(text="✏️ Имя", callback_data="edit_field:name")],
        [InlineKeyboardButton(text="📅 Возраст", callback_data="edit_field:age"),
         InlineKeyboardButton(text="🧑 Пол", callback_data="edit_field:gender")],
        [InlineKeyboardButton(text="🎮 Игры и роли", callback_data="edit_field:games")],
        [InlineKeyboardButton(text="🔥 Стиль игры", callback_data="edit_field:play_style")],
        [InlineKeyboardButton(text="🎤 Микрофон", callback_data="edit_field:mic")],
        [InlineKeyboardButton(text="💬 О себе", callback_data="edit_field:bio")],
        [InlineKeyboardButton(text="⬅ Назад к профилю", callback_data="back_to_profile")],
    ])


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
        "<b>Шаг 1/9</b> · Как тебя называют?\n"
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
        await message.answer("❌ Никнейм должен быть от 2 до 30 символов. Попробуй ещё раз:", reply_markup=back_kb())
        return
    await state.update_data(nickname=text)
    # Переход к шагу 2: Имя
    await state.set_state(Form.name)
    buttons = [[KeyboardButton(text="⬅ Назад")]]
    await message.answer(
        f"✅ Никнейм: <b>{html_mod.escape(text)}</b>\n\n"
        "<b>Шаг 2/9</b> · Какое у тебя имя? (или нажми «➡ Пропустить»):",
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
            "<b>Шаг 1/9</b> · Как тебя называют?\n"
            "Никнейм (2–30 символов):",
            parse_mode="HTML",
            reply_markup=back_kb(),
        )
        return
    if text == "➡ Пропустить":
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
        f"{name_display}\n\n<b>Шаг 3/9</b> · Сколько тебе лет?",
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
            "<b>Шаг 2/9</b> · Какое у тебя имя? (или нажми «➡ Пропустить»):",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
        )
        return
    if message.text not in AGE_GROUPS:
        age_kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=ag)] for ag in AGE_GROUPS] + [[KeyboardButton(text="⬅ Назад")]],
            resize_keyboard=True,
        )
        await message.answer("❌ Выбери возраст кнопкой:", reply_markup=age_kb)
        return
    await state.update_data(age_group=message.text)
    await state.set_state(Form.gender)
    buttons = [[KeyboardButton(text=v)] for v in GENDER_OPTIONS.values()]
    buttons.append([KeyboardButton(text="⬅ Назад")])
    await message.answer(
        f"✅ Возраст: <b>{html_mod.escape(message.text)}</b>\n\n"
        "<b>Шаг 4/9</b> · Пол:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
    )


# ── Шаг 4: Пол ──

@router.message(Form.gender)
async def form_gender(message: Message, state: FSMContext):
    text = message.text
    if text == "⬅ Назад":
        await state.set_state(Form.age)
        buttons = [[KeyboardButton(text=ag)] for ag in AGE_GROUPS]
        buttons.append([KeyboardButton(text="⬅ Назад")])
        await message.answer(
            "Назад к выбору возраста:",
            reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
        )
        return
    if text not in GENDER_OPTIONS.values():
        gender_kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=v)] for v in GENDER_OPTIONS.values()] + [[KeyboardButton(text="⬅ Назад")]],
            resize_keyboard=True,
        )
        await message.answer("❌ Выбери пол кнопкой:", reply_markup=gender_kb)
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
        "🎮 <b>Шаг 5/9</b> · Во что играешь?\n\n"
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
        if data.get("editing_games"):
            # Режим редактирования — назад в меню редактирования
            await state.set_state(Form.edit)
            kb = _edit_menu_kb()
            await message.answer("Назад к редактированию:", reply_markup=kb)
        else:
            await state.set_state(Form.gender)
            buttons = [[KeyboardButton(text=v)] for v in GENDER_OPTIONS.values()]
            buttons.append([KeyboardButton(text="⬅ Назад")])
            await message.answer("Назад к выбору пола:", reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
        return

    if text == "✅ Готово":
        if not selected:
            games_kb = []
            for i in range(0, len(GAMES), 2):
                row = []
                for gk in list(GAMES.keys())[i:i+2]:
                    prefix = "✅ " if gk in selected else ""
                    row.append(KeyboardButton(text=f"{prefix}{GAMES[gk]['icon']} {GAMES[gk]['name']}"))
                games_kb.append(row)
            games_kb.append([KeyboardButton(text="✅ Готово")])
            games_kb.append([KeyboardButton(text="⬅ Назад")])
            await message.answer(
                "❌ Выбери хотя бы одну игру!",
                reply_markup=ReplyKeyboardMarkup(keyboard=games_kb, resize_keyboard=True),
            )
            return

        if data.get("editing_games"):
            # Режим редактирования — сохраняем изменения и возвращаемся в меню
            user_games = await db.get_user_games(message.from_user.id)
            existing_names = {g["game_name"] for g in user_games}
            name_to_key = {gd["name"]: gk for gk, gd in GAMES.items()}
            # Удаляем профили игр, которые больше не выбраны
            for g in user_games:
                gk = name_to_key.get(g["game_name"])
                if gk and gk not in selected:
                    await db.remove_game_profile(message.from_user.id, g["game_name"])
            # Добавляем пустые профили для новых игр
            for gk in selected:
                game_name = GAMES[gk]["name"]
                if game_name not in existing_names:
                    await db.upsert_game_profile(message.from_user.id, game_name, "", "", {})
            await state.set_state(Form.edit)
            kb = _edit_menu_kb()
            await message.answer("✅ Игры обновлены!", reply_markup=kb)
            return

        # Переходим к деталям по первой игре
        await state.update_data(current_game_idx=0, game_details={})
        first_game = selected[0]
        game_data = GAMES[first_game]
        buttons = [[KeyboardButton(text=r)] for r in game_data["roles"]]
        buttons.append([KeyboardButton(text="⬅ Назад")])
        await state.set_state(Form.game_details)
        await message.answer(
            f"🎯 <b>Шаг 6/9</b> · Детали по <b>{game_data['name']}</b>\n\n"
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
        games_kb = []
        for i in range(0, len(GAMES), 2):
            row = []
            for gk in list(GAMES.keys())[i:i+2]:
                prefix = "✅ " if gk in selected else ""
                row.append(KeyboardButton(text=f"{prefix}{GAMES[gk]['icon']} {GAMES[gk]['name']}"))
            games_kb.append(row)
        games_kb.append([KeyboardButton(text="✅ Готово")])
        games_kb.append([KeyboardButton(text="⬅ Назад")])
        await message.answer(
            "❌ Нажми на игру или «✅ Готово»:",
            reply_markup=ReplyKeyboardMarkup(keyboard=games_kb, resize_keyboard=True),
        )
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


# ── Шаг 5: Детали по играм (роль + ранг + платформа + рейтинг) ──

@router.message(Form.game_details)
async def form_game_details(message: Message, state: FSMContext):
    text = message.text
    data = await state.get_data()

    field = data.get("current_detail_field")
    game_key = data.get("current_game_key")
    game_data = GAMES[game_key]
    details = data.get("game_details", {})
    selected = data.get("selected_games", [])
    if game_key not in details:
        details[game_key] = {}

    if text == "⬅ Назад":
        if field in ("rank", "custom_role"):
            # Назад к выбору роли для этой же игры
            await state.update_data(current_detail_field="role")
            buttons = [[KeyboardButton(text=r)] for r in game_data["roles"]]
            buttons.append([KeyboardButton(text="⬅ Назад")])
            await message.answer(
                "Назад к выбору роли:",
                reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
            )
        elif field == "role":
            # Назад к предыдущему шагу
            if data.get("editing_games"):
                # Режим редактирования — назад в меню редактирования
                await state.set_state(Form.edit)
                kb = _edit_menu_kb()
                await message.answer("Назад к редактированию:", reply_markup=kb)
            elif data.get("current_game_idx", 0) > 0:
                # Мы на 2+ игре — вернуться к рангу предыдущей игры
                prev_idx = data["current_game_idx"] - 1
                prev_game_key = selected[prev_idx]
                prev_game_data = GAMES[prev_game_key]
                await state.update_data(current_game_idx=prev_idx, current_game_key=prev_game_key, current_detail_field="rank")
                buttons = [[KeyboardButton(text=r)] for r in prev_game_data["ranks"]]
                buttons.append([KeyboardButton(text="🚫 Нет ранга")])
                buttons.append([KeyboardButton(text="⬅ Назад")])
                await message.answer(
                    f"Назад к <b>{prev_game_data['name']}</b> — выбери ранг:",
                    parse_mode="HTML",
                    reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
                )
            else:
                await state.set_state(Form.games)
                kb = []
                for i in range(0, len(GAMES), 2):
                    row = []
                    for gk in list(GAMES.keys())[i:i+2]:
                        prefix = "✅ " if gk in selected else ""
                        row.append(KeyboardButton(text=f"{prefix}{GAMES[gk]['icon']} {GAMES[gk]['name']}"))
                    kb.append(row)
                kb.append([KeyboardButton(text="✅ Готово")])
                kb.append([KeyboardButton(text="⬅ Назад")])
                await message.answer("Назад к выбору игр:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        else:
            # Другие случаи — назад к выбору игр
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
            kb.append([KeyboardButton(text="⬅ Назад")])
            await message.answer("Назад к выбору игр:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        return

    if field == "role":
        if text == "✏️ Написать свою":
            await state.update_data(current_detail_field="custom_role")
            buttons = [[KeyboardButton(text="⬅ Назад")]]
            await message.answer(
                "✏️ Напиши свою роль (до 30 символов):",
                reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
            )
            return
        if text not in game_data["roles"]:
            role_kb = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=r)] for r in game_data["roles"]] + [[KeyboardButton(text="⬅ Назад")]],
                resize_keyboard=True,
            )
            await message.answer("❌ Выбери роль кнопкой:", reply_markup=role_kb)
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

    if field == "custom_role":
        if text == "⬅ Назад":
            # Вернуться к выбору роли
            buttons = [[KeyboardButton(text=r)] for r in game_data["roles"]]
            buttons.append([KeyboardButton(text="⬅ Назад")])
            await state.update_data(current_detail_field="role")
            await message.answer("Назад к выбору роли:", reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
            return
        if not text or len(text.strip()) < 2:
            await message.answer(
                "❌ Напиши роль длиннее 2 символов:",
                reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅ Назад")]], resize_keyboard=True),
            )
            return
        custom = text.strip()[:30]
        details[game_key]["role"] = custom
        await state.update_data(game_details=details, current_detail_field="rank")
        buttons = [[KeyboardButton(text=r)] for r in game_data["ranks"]]
        buttons.append([KeyboardButton(text="🚫 Нет ранга")])
        buttons.append([KeyboardButton(text="⬅ Назад")])
        await message.answer(
            f"✅ Роль: <b>{html_mod.escape(custom)}</b>\n\n"
            "Выбери свой ранг:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
        )
        return

    if field == "rank":
        if text not in game_data["ranks"] and text != "🚫 Нет ранга":
            rank_kb = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=r)] for r in game_data["ranks"]]
                + [[KeyboardButton(text="🚫 Нет ранга")], [KeyboardButton(text="⬅ Назад")]],
                resize_keyboard=True,
            )
            await message.answer("❌ Выбери ранг кнопкой:", reply_markup=rank_kb)
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
                buttons.append([KeyboardButton(text="➡ Пропустить")])
            else:
                buttons.append([KeyboardButton(text="🚫 Нет")])
                buttons.append([KeyboardButton(text="➡ Пропустить")])
            platform_q = platform.get("question", f"📊 Укажи свой <b>{platform['name']}</b> (или нажми «➡ Пропустить»):")
            await message.answer(
                f"✅ Ранг: <b>{text}</b>\n\n"
                f"{platform_q}",
                parse_mode="HTML",
                reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
            )
        else:
            # Нет платформ — проверяем рейтинг-вопросы
            if _has_rating_questions(game_key):
                await _start_game_rating(message, state, data, details, game_key)
            else:
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
            "🔥 <b>Шаг 7/9</b> · Как ты играешь?\n\n"
            "Выбери до 3 стилей, потом «✅ Далее»:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
        )


# ── Платформа (FaceIt и т.д.) ──

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

    if text == "➡ Пропустить" or text == "🚫 Нет":
        # Пропускаем эту платформу
        pass
    else:
        if platform["options"] and text not in platform["options"]:
            pl_buttons = []
            if platform["options"]:
                pl_buttons = [[KeyboardButton(text=o)] for o in platform["options"]]
                pl_buttons.append([KeyboardButton(text="🚫 Нет")])
            pl_buttons.append([KeyboardButton(text="➡ Пропустить")])
            pl_buttons.append([KeyboardButton(text="⬅ Назад")])
            await message.answer(
                "❌ Выбери кнопкой или нажми «➡ Пропустить»:",
                reply_markup=ReplyKeyboardMarkup(keyboard=pl_buttons, resize_keyboard=True),
            )
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
        buttons.append([KeyboardButton(text="➡ Пропустить")])
        buttons.append([KeyboardButton(text="⬅ Назад")])
        next_platform_q = next_platform.get("question", f"📊 Укажи свой <b>{next_platform['name']}</b> (или «➡ Пропустить»):")
        await message.answer(
            f"{next_platform_q}",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
        )
    else:
        # Все платформы пройдены — собираем extra
        for i, p in enumerate(platforms):
            key = f"platform_{i}"
            if key in details[game_key]:
                details[game_key]["platform_value"] = details[game_key].pop(key)
                details[game_key]["platform_name"] = p["name"]
        await state.update_data(game_details=details)

        # Проверяем рейтинг-вопросы для этой игры
        if _has_rating_questions(game_key):
            await _start_game_rating(message, state, data, details, game_key)
        else:
            await state.set_state(Form.game_details)
            await _save_game_and_advance(message, state, data, details, game_key)


# ── Рейтинг-вопросы внутри каждой игры ──

async def _start_game_rating(message, state, data, details, game_key):
    """Начать задавать рейтинг-вопросы для конкретной игры."""
    await state.set_state(Form.game_rating)
    await state.update_data(current_rating_q_idx=0)
    await _show_game_rating_question(message, game_key, 0)


@router.message(Form.game_rating)
async def form_game_rating(message: Message, state: FSMContext):
    text = message.text
    data = await state.get_data()
    game_key = data.get("current_game_key")
    details = data.get("game_details", {})
    idx = data.get("current_rating_q_idx", 0)
    qs = GAME_RATING_QUESTIONS.get(game_key, [])

    if text == "⬅ Назад":
        if idx > 0:
            # Предыдущий вопрос
            idx -= 1
            await state.update_data(current_rating_q_idx=idx)
            await _show_game_rating_question(message, game_key, idx)
        else:
            # Первый вопрос — назад к платформе или рангу
            game_data = GAMES[game_key]
            platforms = game_data.get("platforms", [])
            if platforms:
                # Назад к платформе
                await state.set_state(Form.platform)
                last_platform_idx = len(platforms) - 1
                await state.update_data(current_platform_idx=last_platform_idx)
                platform = platforms[last_platform_idx]
                buttons = []
                if platform["options"]:
                    buttons = [[KeyboardButton(text=o)] for o in platform["options"]]
                    buttons.append([KeyboardButton(text="🚫 Нет")])
                buttons.append([KeyboardButton(text="➡ Пропустить")])
                buttons.append([KeyboardButton(text="⬅ Назад")])
                platform_q = platform.get("question", f"📊 Укажи свой <b>{platform['name']}</b> (или «➡ Пропустить»):")
                await message.answer(
                    "Назад к платформе:",
                    parse_mode="HTML",
                    reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
                )
            else:
                # Назад к выбору ранга
                await state.set_state(Form.game_details)
                await state.update_data(current_detail_field="rank")
                buttons = [[KeyboardButton(text=r)] for r in game_data["ranks"]]
                buttons.append([KeyboardButton(text="🚫 Нет ранга")])
                buttons.append([KeyboardButton(text="⬅ Назад")])
                await message.answer("Назад к выбору ранга:", reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
        return

    # Сохраняем ответ
    q = qs[idx]
    field = q["field"]

    if text == "➡ Пропустить":
        value = ""
    elif text == "🚫 Нет":
        value = ""
    elif text == "✅ Да":
        value = "Да"
    elif text == "❌ Нет":
        value = "Нет"
    else:
        value = text[:100]

    # Сохраняем в details (потом при save_game_and_advance запишется в БД)
    if game_key not in details:
        details[game_key] = {}
    details[game_key][field] = value
    await state.update_data(game_details=details)

    # Следующий вопрос или завершение
    idx += 1
    if idx < len(qs):
        await state.update_data(current_rating_q_idx=idx)
        await _show_game_rating_question(message, game_key, idx)
    else:
        # Все вопросы этой игры пройдены → сохраняем и переход к следующей игре
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
            style_kb = []
            for s in PLAY_STYLES:
                prefix = "✅ " if s in styles else ""
                style_kb.append([KeyboardButton(text=f"{prefix}{s}")])
            for s in styles:
                if s not in PLAY_STYLES:
                    style_kb.append([KeyboardButton(text=f"✅ {s}")])
            style_kb.append([KeyboardButton(text="✏️ Написать свой")])
            style_kb.append([KeyboardButton(text="✅ Далее")])
            style_kb.append([KeyboardButton(text="⬅ Назад")])
            await message.answer(
                "❌ Выбери хотя бы один стиль!",
                reply_markup=ReplyKeyboardMarkup(keyboard=style_kb, resize_keyboard=True),
            )
            return
        await db.update_user(message.from_user.id, play_style=json.dumps(styles))
        # Шаг 7: Микро и язык
        await state.set_state(Form.mic)
        buttons = [[KeyboardButton(text=v)] for v in MIC_OPTIONS.values()]
        buttons.append([KeyboardButton(text="⬅ Назад")])
        await message.answer(
            "🎤 <b>Шаг 8/9</b> · Готов voice-чатить?\n\n"
            "Выбери вариант:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
        )
        return

    if text == "✏️ Написать свой":
        await state.set_state(Form.custom_style)
        await message.answer(
            "✏️ Напиши свой стиль (до 30 символов):",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅ Назад")]], resize_keyboard=True),
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
        # Too many styles
        max_kb = []
        for s in PLAY_STYLES:
            prefix = "✅ " if s in styles else ""
            max_kb.append([KeyboardButton(text=f"{prefix}{s}")])
        for s in styles:
            if s not in PLAY_STYLES:
                max_kb.append([KeyboardButton(text=f"✅ {s}")])
        max_kb.append([KeyboardButton(text="✏️ Написать свой")])
        max_kb.append([KeyboardButton(text="✅ Далее")])
        max_kb.append([KeyboardButton(text="⬅ Назад")])
        await message.answer(
            "❌ Максимум 3 стиля!",
            reply_markup=ReplyKeyboardMarkup(keyboard=max_kb, resize_keyboard=True),
        )
        return

    await state.update_data(selected_styles=styles)

    kb = []
    for s in PLAY_STYLES:
        prefix = "✅ " if s in styles else ""
        kb.append([KeyboardButton(text=f"{prefix}{s}")])
    # Show custom styles
    for s in styles:
        if s not in PLAY_STYLES:
            kb.append([KeyboardButton(text=f"✅ {s}")])
    kb.append([KeyboardButton(text="✏️ Написать свой")])
    kb.append([KeyboardButton(text="✅ Далее")])
    kb.append([KeyboardButton(text="⬅ Назад")])
    await message.answer(
        f"Выбрано: <b>{len(styles)}/3</b>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True),
    )


# ── Ввод своего стиля ──

@router.message(Form.custom_style)
async def form_custom_style(message: Message, state: FSMContext):
    text = message.text

    if text == "⬅ Назад":
        await state.set_state(Form.play_style)
        data = await state.get_data()
        styles = data.get("selected_styles", [])
        kb = []
        for s in PLAY_STYLES:
            prefix = "✅ " if s in styles else ""
            kb.append([KeyboardButton(text=f"{prefix}{s}")])
        kb.append([KeyboardButton(text="✏️ Написать свой")])
        kb.append([KeyboardButton(text="✅ Далее")])
        kb.append([KeyboardButton(text="⬅ Назад")])
        await message.answer(
            f"Выбрано: <b>{len(styles)}/3</b>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True),
        )
        return

    if not text or len(text.strip()) < 2:
        await message.answer(
            "❌ Напиши стиль длиннее 2 символов:",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅ Назад")]], resize_keyboard=True),
        )
        return

    custom = text.strip()[:30]
    data = await state.get_data()
    styles = data.get("selected_styles", [])

    # Проверка на дубликат
    if custom in styles:
        await message.answer(
            "❌ Этот стиль уже выбран!",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅ Назад")]], resize_keyboard=True),
        )
        return

    if len(styles) < 3:
        styles.append(custom)
    else:
        await message.answer("❌ Максимум 3 стиля!")
        return

    await state.update_data(selected_styles=styles)

    # Вернуться к выбору стилей
    await state.set_state(Form.play_style)
    kb = []
    for s in PLAY_STYLES:
        prefix = "✅ " if s in styles else ""
        kb.append([KeyboardButton(text=f"{prefix}{s}")])
    # Показать кастомный стиль как выбранный
    for s in styles:
        if s not in PLAY_STYLES:
            kb.append([KeyboardButton(text=f"✅ {s}")])
    kb.append([KeyboardButton(text="✏️ Написать свой")])
    kb.append([KeyboardButton(text="✅ Далее")])
    kb.append([KeyboardButton(text="⬅ Назад")])
    await message.answer(
        f"✅ Стиль: <b>{html_mod.escape(custom)}</b>\n\n"
        f"Выбрано: <b>{len(styles)}/3</b>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True),
    )


# ── Шаг 7: Микрофон ──

@router.message(Form.mic)
async def form_mic(message: Message, state: FSMContext):
    text = message.text

    if text == "⬅ Назад":
        # Восстанавливаем стили из БД, чтобы не потерять
        user = await db.get_user(message.from_user.id)
        saved_styles = json.loads(user.get("play_style", "[]") or "[]") if user else []
        await state.set_state(Form.play_style)
        await state.update_data(selected_styles=saved_styles)
        kb = []
        for s in PLAY_STYLES:
            prefix = "✅ " if s in saved_styles else ""
            kb.append([KeyboardButton(text=f"{prefix}{s}")])
        for s in saved_styles:
            if s not in PLAY_STYLES:
                kb.append([KeyboardButton(text=f"✅ {s}")])
        kb.append([KeyboardButton(text="✏️ Написать свой")])
        kb.append([KeyboardButton(text="✅ Далее")])
        kb.append([KeyboardButton(text="⬅ Назад")])
        await message.answer(
            f"Назад к стилям игры (выбрано: {len(saved_styles)}/3):",
            reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True),
        )
        return

    if text not in MIC_OPTIONS.values():
        mic_kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=v)] for v in MIC_OPTIONS.values()] + [[KeyboardButton(text="⬅ Назад")]],
            resize_keyboard=True,
        )
        await message.answer("❌ Выбери вариант кнопкой:", reply_markup=mic_kb)
        return

    mic = [k for k, v in MIC_OPTIONS.items() if v == text][0]
    await db.update_user(message.from_user.id, mic_status=mic)

    # Шаг 8: Био
    await state.set_state(Form.bio)
    await message.answer(
        f"✅ Микро: <b>{text}</b>\n\n"
        "📝 <b>Шаг 9/9</b> · Расскажи о себе (необязательно):\n\n"
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


# ── Шаг 8: О себе ──

@router.message(Form.bio)
async def form_bio(message: Message, state: FSMContext):
    text = message.text

    if text == "⬅ Назад":
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
        rank_display = g.get("rank", "") or "Без ранга"
        extra_str = " · ".join(extra_parts)
        line = f"{game_icon} {g['game_name']} · {rank_display}{role_str}"
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

    kb = []
    for g in games:
        # Find icon
        icon = "🎮"
        for gk, gd in GAMES.items():
            if gd["name"] == g["game_name"]:
                icon = gd["icon"]
                break
        kb.append([KeyboardButton(text=f"{icon} {g['game_name']}")])
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
        # Match "icon GameName" format
        game_filter = None
        for gk, gd in GAMES.items():
            if text == f"{gd['icon']} {gd['name']}":
                game_filter = gd["name"]
                break
        if game_filter is None:
            await message.answer("❌ Выбери игру кнопкой:")
            return

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
        rank_display = g.get("rank", "") or "Без ранга"
        extra = json.loads(g.get("extra_fields", "{}") or "{}")
        extra_parts = _format_extra_fields(extra)
        lines = f"  {game_icon} {g['game_name']} · {rank_display}{role_str}"
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
        rank_display = g.get("rank", "") or "Без ранга"
        extra_str = " · ".join(extra_parts)
        line = f"{game_icon} {g['game_name']} · {rank_display}{role_str}"
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
        f"⭐ В избранном у: <b>{len(favorites)}</b>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_profile")],
    ])

    await message.answer(text, reply_markup=kb, parse_mode="HTML")


# ── Редактирование профиля ──

@router.callback_query(F.data == "edit_profile")
async def cb_edit_profile(callback: CallbackQuery, state: FSMContext):
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Анкета не найдена", show_alert=True)
        return

    await state.set_state(Form.edit)
    await callback.message.answer(
        "✏️ <b>Редактирование профиля</b>\n\n"
        "Что хочешь изменить?",
        parse_mode="HTML",
        reply_markup=_edit_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_profile")
async def cb_back_to_profile(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("❌ Анкета не найдена.")
        await callback.answer()
        return

    games = await db.get_user_games(callback.from_user.id)
    favorites = await db.get_user_favorites(callback.from_user.id)

    gender_text = GENDER_OPTIONS.get(user.get("gender", "hidden"), "")
    mic_text = MIC_OPTIONS.get(user.get("mic_status", "no_mic"), "")
    games_lines = []
    for g in games:
        extra = json.loads(g.get("extra_fields", "{}") or "{}")
        extra_parts = _format_extra_fields(extra)
        game_icon = "🎮"
        for gk, gd in GAMES.items():
            if gd["name"] == g["game_name"]:
                game_icon = gd["icon"]
                break
        role_str = f" · {g['role']}" if g.get("role") else ""
        rank_display = g.get("rank", "") or "Без ранга"
        extra_str = " · ".join(extra_parts)
        line = f"{game_icon} {g['game_name']} · {rank_display}{role_str}"
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
        f"⭐ В избранном у: <b>{len(favorites)}</b>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_profile")],
    ])

    await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ── Выбор поля для редактирования ──

@router.callback_query(F.data.startswith("edit_field:"))
async def cb_edit_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split(":")[1]
    await state.update_data(edit_field=field)
    await callback.answer()

    if field == "nickname":
        await state.set_state(Form.edit_text)
        await callback.message.answer(
            "✏️ Введи новый никнейм (2–30 символов):",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅ Отмена")]], resize_keyboard=True),
        )

    elif field == "name":
        await state.set_state(Form.edit_text)
        await callback.message.answer(
            "✏️ Введи новое имя (или «⬅ Отмена»):",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅ Отмена")]], resize_keyboard=True),
        )

    elif field == "bio":
        await state.set_state(Form.edit_text)
        await callback.message.answer(
            "✏️ Расскажи о себе заново (или «⬅ Отмена»):",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅ Отмена")]], resize_keyboard=True),
        )

    elif field == "age":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=ag, callback_data=f"edit_save:age:{ag}")] for ag in AGE_GROUPS
        ] + [[InlineKeyboardButton(text="⬅ Отмена", callback_data="edit_cancel")]])
        await callback.message.answer("📅 Сколько тебе лет?", reply_markup=kb)

    elif field == "gender":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=v, callback_data=f"edit_save:gender:{k}")] for k, v in GENDER_OPTIONS.items()
        ] + [[InlineKeyboardButton(text="⬅ Отмена", callback_data="edit_cancel")]])
        await callback.message.answer("🧑 Выбери пол:", reply_markup=kb)

    elif field == "mic":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=v, callback_data=f"edit_save:mic:{k}")] for k, v in MIC_OPTIONS.items()
        ] + [[InlineKeyboardButton(text="⬅ Отмена", callback_data="edit_cancel")]])
        await callback.message.answer("🎤 Микрофон:", reply_markup=kb)

    elif field == "play_style":
        # Загружаем текущие стили из БД
        user = await db.get_user(callback.from_user.id)
        saved_styles = json.loads(user.get("play_style", "[]") or "[]") if user else []
        await state.set_state(Form.edit)
        await state.update_data(edit_styles=list(saved_styles))
        kb_buttons = []
        for s in PLAY_STYLES:
            prefix = "✅ " if s in saved_styles else ""
            kb_buttons.append([InlineKeyboardButton(text=f"{prefix}{s}", callback_data=f"edit_toggle_style:{s}")])
        # Показать кастомные стили
        for s in saved_styles:
            if s not in PLAY_STYLES:
                kb_buttons.append([InlineKeyboardButton(text=f"✅ {s}", callback_data=f"edit_toggle_style:{s}")])
        kb_buttons.append([InlineKeyboardButton(text="✅ Готово", callback_data="edit_save_style")])
        kb_buttons.append([InlineKeyboardButton(text="⬅ Отмена", callback_data="edit_cancel")])
        await callback.message.answer(
            f"🔥 Выбери стиль игры (выбрано: {len(saved_styles)}/3):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons),
        )

    elif field == "games":
        # Показать список игр для редактирования деталей
        user = await db.get_user(callback.from_user.id)
        games = await db.get_user_games(callback.from_user.id)
        game_names = [g["game_name"] for g in games]

        kb_buttons = []
        for gk, gd in GAMES.items():
            if gd["name"] in game_names:
                kb_buttons.append([InlineKeyboardButton(
                    text=f"{gd['icon']} {gd['name']}",
                    callback_data=f"edit_game:{gk}",
                )])
        # Also allow adding/removing games
        kb_buttons.append([InlineKeyboardButton(text="➕ Добавить / убрать игры", callback_data="edit_toggle_games")])
        kb_buttons.append([InlineKeyboardButton(text="⬅ Отмена", callback_data="edit_cancel")])
        await callback.message.answer(
            "🎮 Какую игру редактировать?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons),
        )


# ── Сохранение выбора (age, gender, mic) ──

@router.callback_query(F.data.startswith("edit_save:"))
async def cb_edit_save(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    field = parts[1]
    value = parts[2]
    await callback.answer("✅ Сохранено!")

    if field == "age":
        await db.update_user(callback.from_user.id, age_group=value)
    elif field == "gender":
        await db.update_user(callback.from_user.id, gender=value)
    elif field == "mic":
        await db.update_user(callback.from_user.id, mic_status=value)

    # Вернуться к меню редактирования
    kb = _edit_menu_kb()
    await state.set_state(Form.edit)
    await callback.message.answer("✏️ Что ещё изменить?", reply_markup=kb)


# ── Стиль игры (toggle) ──

@router.callback_query(F.data.startswith("edit_toggle_style:"))
async def cb_edit_toggle_style(callback: CallbackQuery, state: FSMContext):
    style = callback.data.split(":", 1)[1]
    data = await state.get_data()
    styles = data.get("edit_styles", [])

    if style in styles:
        styles.remove(style)
    elif len(styles) < 3:
        styles.append(style)
    else:
        await callback.answer("❌ Максимум 3 стиля!", show_alert=True)
        return

    await state.update_data(edit_styles=styles)
    await callback.answer(f"{'✅' if style in styles else '➖'} {style}")

    # Rebuild keyboard
    kb_buttons = []
    for s in PLAY_STYLES:
        prefix = "✅ " if s in styles else ""
        kb_buttons.append([InlineKeyboardButton(text=f"{prefix}{s}", callback_data=f"edit_toggle_style:{s}")])
    # Показать кастомные стили
    for s in styles:
        if s not in PLAY_STYLES:
            kb_buttons.append([InlineKeyboardButton(text=f"✅ {s}", callback_data=f"edit_toggle_style:{s}")])
    kb_buttons.append([InlineKeyboardButton(text=f"✅ Готово ({len(styles)}/3)", callback_data="edit_save_style")])
    kb_buttons.append([InlineKeyboardButton(text="⬅ Отмена", callback_data="edit_cancel")])
    await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons))


@router.callback_query(F.data == "edit_save_style")
async def cb_edit_save_style(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    styles = data.get("edit_styles", [])
    if not styles:
        await callback.answer("❌ Выбери хотя бы один стиль!", show_alert=True)
        return

    await db.update_user(callback.from_user.id, play_style=json.dumps(styles))
    await callback.answer("✅ Стиль сохранён!")

    # Вернуться к меню
    kb = _edit_menu_kb()
    await state.set_state(Form.edit)
    await callback.message.answer("✏️ Что ещё изменить?", reply_markup=kb)


@router.callback_query(F.data == "edit_cancel")
async def cb_edit_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена редактирования — вернуться к меню редактирования."""
    kb = _edit_menu_kb()
    await state.set_state(Form.edit)
    await callback.message.answer("✏️ Отменено. Что ещё изменить?", reply_markup=kb)
    await callback.answer()


# ── Редактирование игр ──

@router.callback_query(F.data.startswith("edit_game:"))
async def cb_edit_game(callback: CallbackQuery, state: FSMContext):
    game_key = callback.data.split(":")[1]
    game_data = GAMES[game_key]
    await state.update_data(edit_game_key=game_key)
    await callback.answer()

    user = await db.get_user(callback.from_user.id)
    games = await db.get_user_games(callback.from_user.id)

    # Find current profile for this game
    current = None
    for g in games:
        if g["game_name"] == game_data["name"]:
            current = g
            break

    current_role = current["role"] if current else ""
    current_rank = current["rank"] if current else "Без ранга"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🎯 Роль: {current_role}", callback_data="edit_game_field:role")],
        [InlineKeyboardButton(text=f"🏆 Ранг: {current_rank or 'Без ранга'}", callback_data="edit_game_field:rank")],
    ])

    # Add platform button if game has platforms
    platforms = game_data.get("platforms", [])
    if platforms:
        extra = json.loads(current.get("extra_fields", "{}") or "{}") if current else {}
        platform_val = "Не указано"
        for k, v in extra.items():
            if k.startswith("platform") and v:
                platform_val = v
                break
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"📊 Платформа: {platform_val}", callback_data="edit_game_field:platform")])

    # Add rating button if game has rating questions
    if _has_rating_questions(game_key):
        extra = json.loads(current.get("extra_fields", "{}") or "{}") if current else {}
        rating_info = []
        for q in GAME_RATING_QUESTIONS.get(game_key, []):
            val = extra.get(q["field"], "")
            if val:
                rating_info.append(val)
        rating_text = " · ".join(rating_info) if rating_info else "Не указано"
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"⭐ Рейтинг: {rating_text}", callback_data="edit_game_field:rating")])

    kb.inline_keyboard.append([InlineKeyboardButton(text="⬅ Назад", callback_data="edit_field:games")])

    await state.set_state(Form.edit)
    await callback.message.answer(
        f"{game_data['icon']} <b>Редактирование: {game_data['name']}</b>\n\n"
        f"Роль: {current_role}\n"
        f"Ранг: {current_rank or 'Без ранга'}",
        parse_mode="HTML",
        reply_markup=kb,
    )


@router.callback_query(F.data == "edit_toggle_games")
async def cb_edit_toggle_games(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    # Go back to questionnaire games step
    selected = []
    games = await db.get_user_games(callback.from_user.id)
    # Find current game keys
    name_to_key = {gd["name"]: gk for gk, gd in GAMES.items()}
    for g in games:
        if g["game_name"] in name_to_key:
            selected.append(name_to_key[g["game_name"]])

    await state.set_state(Form.games)
    await state.update_data(selected_games=selected, editing_games=True)
    kb = []
    for i in range(0, len(GAMES), 2):
        row = []
        for gk in list(GAMES.keys())[i:i+2]:
            prefix = "✅ " if gk in selected else ""
            row.append(KeyboardButton(text=f"{prefix}{GAMES[gk]['icon']} {GAMES[gk]['name']}"))
        kb.append(row)
    kb.append([KeyboardButton(text="✅ Готово")])
    kb.append([KeyboardButton(text="⬅ Назад")])
    await callback.message.answer(
        "🎮 Выбери игры (нажми чтобы убрать/добавить):",
        reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True),
    )


# ── Редактирование конкретного поля игры ──

@router.callback_query(F.data == "edit_game_field:role")
async def cb_edit_game_role(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    game_key = data.get("edit_game_key")
    game_data = GAMES[game_key]
    await callback.answer()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=r, callback_data=f"edit_game_val:role:{r}")] for r in game_data["roles"]
    ] + [[InlineKeyboardButton(text="✏️ Своя роль", callback_data="edit_game_text:role")],
         [InlineKeyboardButton(text="⬅ Назад", callback_data=f"edit_game:{game_key}")]])
    await callback.message.answer("🎯 Выбери роль:", reply_markup=kb)


@router.callback_query(F.data == "edit_game_field:rank")
async def cb_edit_game_rank(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    game_key = data.get("edit_game_key")
    game_data = GAMES[game_key]
    await callback.answer()

    buttons = [InlineKeyboardButton(text=r, callback_data=f"edit_game_val:rank:{r}") for r in game_data["ranks"]]
    # Split into rows of 2
    rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(text="🚫 Нет ранга", callback_data="edit_game_val:rank:🚫 Нет ранга")])
    rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data=f"edit_game:{game_key}")])
    await callback.message.answer("🏆 Выбери ранг:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data == "edit_game_field:platform")
async def cb_edit_game_platform(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    game_key = data.get("edit_game_key")
    game_data = GAMES[game_key]
    platforms = game_data.get("platforms", [])
    await callback.answer()

    if not platforms:
        return

    platform = platforms[0]
    buttons = []
    if platform["options"]:
        buttons = [InlineKeyboardButton(text=o, callback_data=f"edit_game_val:platform:{o}") for o in platform["options"]]
        rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    else:
        rows = []

    rows.append([InlineKeyboardButton(text="🚫 Нет", callback_data="edit_game_val:platform:🚫 Нет")])
    rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data=f"edit_game:{game_key}")])

    platform_q = platform.get("question", f"📊 {platform['name']}:")
    await callback.message.answer(platform_q, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data == "edit_game_field:rating")
async def cb_edit_game_rating(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    game_key = data.get("edit_game_key")
    await callback.answer()

    qs = GAME_RATING_QUESTIONS.get(game_key, [])
    if not qs:
        return

    kb_buttons = []
    for q in qs:
        kb_buttons.append([InlineKeyboardButton(text=q["text"], callback_data=f"edit_game_text:{q['field']}")])
    kb_buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data=f"edit_game:{game_key}")])

    await callback.message.answer("⭐ Что изменить?", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons))


# ── Сохранение значения поля игры (callback с value) ──

@router.callback_query(F.data.startswith("edit_game_val:"))
async def cb_edit_game_val(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":", 2)
    field = parts[1]
    value = parts[2]
    data = await state.get_data()
    game_key = data.get("edit_game_key")
    game_name = GAMES[game_key]["name"]
    user_id = callback.from_user.id

    await callback.answer("✅ Сохранено!")

    # Get current profile
    games = await db.get_user_games(user_id)
    current = None
    for g in games:
        if g["game_name"] == game_name:
            current = g
            break

    extra = json.loads(current.get("extra_fields", "{}") or "{}") if current else {}
    rank = current.get("rank", "") if current else ""
    role = current.get("role", "") if current else ""

    if field == "role":
        role = value
    elif field == "rank":
        rank = "" if value == "🚫 Нет ранга" else value
    elif field == "platform":
        # Сохраняем только именованный ключ платформы (без дублей)
        platforms = GAMES[game_key].get("platforms", [])
        if platforms:
            # Убираем старые служебные ключи
            extra.pop("platform_name", None)
            extra.pop("platform_value", None)
            extra[platforms[0]["name"]] = value if value != "🚫 Нет" else ""

    await db.upsert_game_profile(user_id, game_name, rank, role, extra)

    # Go back to game edit
    await callback.message.edit_reply_markup()  # Clear buttons
    # Re-show game edit
    current_role = role
    current_rank = rank or "Без ранга"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🎯 Роль: {current_role}", callback_data="edit_game_field:role")],
        [InlineKeyboardButton(text=f"🏆 Ранг: {current_rank}", callback_data="edit_game_field:rank")],
    ])
    if GAMES[game_key].get("platforms"):
        platform_val = extra.get(GAMES[game_key]["platforms"][0]["name"], "") or "Не указано"
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"📊 Платформа: {platform_val}", callback_data="edit_game_field:platform")])
    if _has_rating_questions(game_key):
        rating_info = []
        for q in GAME_RATING_QUESTIONS.get(game_key, []):
            val = extra.get(q["field"], "")
            if val:
                rating_info.append(val)
        rating_text = " · ".join(rating_info) if rating_info else "Не указано"
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"⭐ Рейтинг: {rating_text}", callback_data="edit_game_field:rating")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="⬅ Назад", callback_data="edit_field:games")])

    await callback.message.answer(
        f"{GAMES[game_key]['icon']} <b>{game_name}</b>\n\n"
        f"Роль: {current_role}\n"
        f"Ранг: {current_rank}",
        parse_mode="HTML",
        reply_markup=kb,
    )


# ── Редактирование текстовых полей игры (своя роль, MMR, etc.) ──

@router.callback_query(F.data.startswith("edit_game_text:"))
async def cb_edit_game_text(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split(":", 1)[1]
    await state.update_data(edit_field=f"game_{field}")
    await callback.answer()
    await state.set_state(Form.edit_text)
    await callback.message.answer(
        "✏️ Введи новое значение:",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅ Отмена")]], resize_keyboard=True),
    )


# ── Обработка текстового ввода при редактировании ──

@router.message(Form.edit_text)
async def form_edit_text(message: Message, state: FSMContext):
    text = message.text
    data = await state.get_data()
    field = data.get("edit_field", "")

    if text == "⬅ Отмена":
        # Вернуться к меню редактирования
        kb = _edit_menu_kb()
        await state.set_state(Form.edit)
        await message.answer("✏️ Отменено. Что ещё изменить?", reply_markup=kb)
        return

    if field == "nickname":
        if len(text) < 2 or len(text) > 30:
            await message.answer("❌ От 2 до 30 символов:")
            return
        await db.update_user(message.from_user.id, nickname=text)
        await message.answer(f"✅ Никнейм: <b>{html_mod.escape(text)}</b>", parse_mode="HTML")

    elif field == "name":
        name = text.strip()[:30]
        await db.update_user(message.from_user.id, name=name)
        await message.answer(f"✅ Имя: <b>{html_mod.escape(name)}</b>" if name else "✅ Имя убрано", parse_mode="HTML")

    elif field == "bio":
        bio = text[:500]
        await db.update_user(message.from_user.id, bio=bio)
        await message.answer("✅ О себе обновлено!")

    elif field.startswith("game_"):
        # Edit game-specific text field (role, mmr, etc.)
        game_field = field[5:]  # remove "game_" prefix
        data2 = await state.get_data()
        game_key = data2.get("edit_game_key")
        game_name = GAMES[game_key]["name"]
        user_id = message.from_user.id

        games = await db.get_user_games(user_id)
        current = None
        for g in games:
            if g["game_name"] == game_name:
                current = g
                break

        extra = json.loads(current.get("extra_fields", "{}") or "{}") if current else {}
        rank = current.get("rank", "") if current else ""
        role = current.get("role", "") if current else ""

        if game_field == "role":
            role = text.strip()[:30]
        else:
            extra[game_field] = text.strip()[:100]

        await db.upsert_game_profile(user_id, game_name, rank, role, extra)
        await message.answer(f"✅ Сохранено: <b>{text.strip()[:50]}</b>", parse_mode="HTML")

        # Return to game edit
        # (Will show next message via inline)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅ К игре", callback_data=f"edit_game:{game_key}")],
            [InlineKeyboardButton(text="⬅ К профилю", callback_data="back_to_profile")],
        ])
        await message.answer("Что дальше?", reply_markup=kb)
        return

    else:
        await message.answer("❌ Неизвестное поле.")
        return

    # Return to edit menu
    kb = _edit_menu_kb()
    await state.set_state(Form.edit)
    await message.answer("✅ Сохранено! Что ещё изменить?", reply_markup=kb)


# ── Поддержка ──

@router.message(F.text == "💬 Поддержка")
async def support_start(message: Message, state: FSMContext):
    await state.set_state(Form.support)
    await message.answer(
        "💬 <b>Поддержка</b>\n\n"
        "Напиши своё сообщение, и оно будет анонимно переслано разработчику.\n\n"
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
    await state.clear()
    await message.answer("🏠 В главное меню:", reply_markup=main_kb())


# ── Запуск ──

async def main():
    await db.init_db()
    logging.info("DuoQ Bot запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
