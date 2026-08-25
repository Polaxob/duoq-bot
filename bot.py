"""
DuoQ — Основной файл бота
Запуск: python bot.py
"""

import asyncio
import logging
import json
import os
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
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

logging.basicConfig(level=logging.INFO)

# ── Данные игр ──

GAMES = {
    "cs2": {
        "name": "CS2",
        "ranks": ["Silver I", "Silver II", "Silver III", "Silver IV", "Silver Elite",
                  "Gold Nova I", "Gold Nova II", "Gold Nova III", "Gold Nova Master",
                  "Master Guardian I", "Master Guardian II", "Master Guardian Elite",
                  "Distinguished Master Guardian", "Legendary Eagle", "Legendary Eagle Master",
                  "Supreme Master", "Global Elite"],
        "roles": ["Rifler", "AWP", "IGL", "Support", "Entry"],
    },
    "dota2": {
        "name": "Dota 2",
        "ranks": ["Herald", "Guardian", "Crusader", "Archon", "Legend", "Ancient", "Divine", "Immortal"],
        "roles": ["Carry", "Mid", "Offlane", "Soft Support", "Hard Support"],
    },
    "valorant": {
        "name": "Valorant",
        "ranks": ["Iron", "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Ascendant", "Immortal", "Radiant"],
        "roles": ["Duelist", "Sentinel", "Controller", "Initiator"],
    },
    "fortnite": {
        "name": "Fortnite",
        "ranks": ["Bot", "Новичок", "Средний", "Выше среднего", "Продвинутый", "Эксперт"],
        "roles": ["Build", "No-Build", "Оба режима"],
    },
    "apex": {
        "name": "Apex Legends",
        "ranks": ["Bronze", "Silver", "Gold", "Platinum", "Diamond", "Master", "Predator"],
        "roles": ["Танк", "Урон", "Поддержка"],
    },
    "pubg": {
        "name": "PUBG",
        "ranks": ["Bronze", "Silver", "Gold", "Platinum", "Diamond", "Master"],
        "roles": ["Агрессивный", "Пассивный", "Универсал"],
    },
    "rust": {
        "name": "Rust",
        "ranks": ["Новичок", "Средний", "Опытный", "Профи"],
        "roles": ["PvP", "PvE", "Builder", "Raid"],
    },
    "minecraft": {
        "name": "Minecraft",
        "ranks": ["Новичок", "Средний", "Опытный", "Профи"],
        "roles": ["SMP", "Creative", "Modded", "PvP", "Speedrun"],
    },
    "gtav": {
        "name": "GTA V",
        "ranks": ["Новичок", "Средний", "Опытный", "Профи"],
        "roles": ["Heists", "RP", "PvP", "Кэш-хант"],
    },
    "league": {
        "name": "League of Legends",
        "ranks": ["Iron", "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Master", "Grandmaster", "Challenger"],
        "roles": ["Top", "Jungle", "Mid", "ADC", "Support"],
    },
    "rl": {
        "name": "Rocket League",
        "ranks": ["Bronze", "Silver", "Gold", "Platinum", "Diamond", "Champion", "Grand Champion", "SSL"],
        "roles": ["2v2", "3v3", "1v1"],
    },
    "dayz": {
        "name": "DayZ",
        "ranks": ["Новичок", "Средний", "Опытный", "Профи"],
        "roles": ["PvP", "PvE", "Roleplay"],
    },
}

AGE_GROUPS = ["<16", "16-18", "18-25", "25+"]
GENDER_OPTIONS = {"male": "🧑 Мужской", "female": "👩 Женский", "hidden": "🤔 Не указывать"}
LANGUAGES = {"ru": "🇷🇺 Русский", "en": "🇬🇧 English", "uk": "🇺🇦 Українська", "de": "🇩🇪 Deutsch"}
PLAY_STYLES = ["🔥 Агрессивно", "🧊 Спокойно", "🧠 Стратегически",
               "😂 Развлекаясь", "🏆 Рейтингово", "🎮 Казуально",
               "😤 Соло", "🤝 Командно"]
MIC_OPTIONS = {"mic": "🎤 Микро есть", "listen": "🎧 Только слушаю", "no_mic": "🔇 Нет микрофона"}

# ── FSM для создания анкеты ──

class Form(StatesGroup):
    nickname = State()
    age = State()
    gender = State()
    games = State()
    game_details = State()
    play_style = State()
    mic = State()
    bio = State()
    # Поиск
    search_game = State()
    # Настройки
    settings = State()


# ── Клавиатуры ──

def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Создать анкету"), KeyboardButton(text="🔍 Найти тиммейтов")],
            [KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="⚙️ Настройки")],
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
            f"🎮 <b>С возвращением, {user['nickname']}!</b>\n\n"
            "Что хочешь сделать?"
        )
    await message.answer(text, reply_markup=main_kb(), parse_mode="HTML")


@router.message(F.text == "📋 Создать анкету")
async def start_form(message: Message, state: FSMContext):
    await state.set_state(Form.nickname)
    await message.answer(
        "📝 <b>Создание анкеты</b>\n\n"
        "<b>Шаг 1/8</b> · Как тебя называют?\n"
        "Напиши свой ник или имя (2–30 символов):",
        parse_mode="HTML",
        reply_markup=back_kb(),
    )


# ── Шаг 1: Ник ──

@router.message(Form.nickname)
async def form_nickname(message: Message, state: FSMContext):
    text = message.text.strip()
    if len(text) < 2 or len(text) > 30:
        await message.answer("❌ Ник должен быть от 2 до 30 символов. Попробуй ещё раз:")
        return
    await state.update_data(nickname=text)
    await state.set_state(Form.age)
    buttons = [[KeyboardButton(text=ag)] for ag in AGE_GROUPS]
    buttons.append([KeyboardButton(text="⬅ Назад")])
    await message.answer(
        f"✅ Ник: <b>{text}</b>\n\n"
        "<b>Шаг 2/8</b> · Сколько тебе лет?",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
    )


# ── Шаг 2: Возраст ──

@router.message(Form.age)
async def form_age(message: Message, state: FSMContext):
    if message.text not in AGE_GROUPS:
        await message.answer("❌ Выбери возраст кнопкой:")
        return
    await state.update_data(age_group=message.text)
    await state.set_state(Form.gender)
    buttons = [[KeyboardButton(text=v)] for v in GENDER_OPTIONS.values()]
    buttons.append([KeyboardButton(text="⬅ Назад")])
    await message.answer(
        f"✅ Возраст: <b>{message.text}</b>\n\n"
        "<b>Шаг 3/8</b> · Пол:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
    )


# ── Шаг 3: Пол ──

@router.message(Form.gender)
async def form_gender(message: Message, state: FSMContext):
    text = message.text
    if text not in GENDER_OPTIONS.values():
        await message.answer("❌ Выбери пол кнопкой:")
        return
    gender = [k for k, v in GENDER_OPTIONS.items() if v == text][0]
    await state.update_data(gender=gender)
    await state.set_state(Form.games)
    kb = []
    for i in range(0, len(GAMES), 2):
        row = []
        for gk in list(GAMES.keys())[i:i+2]:
            row.append(KeyboardButton(text=f"🎮 {GAMES[gk]['name']}"))
        kb.append(row)
    kb.append([KeyboardButton(text="✅ Готово")])
    kb.append([KeyboardButton(text="⬅ Назад")])
    await message.answer(
        "🎮 <b>Шаг 4/8</b> · Во что играешь?\n\n"
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
            f"🎯 <b>Шаг 5/8</b> · Детали по <b>{game_data['name']}</b>\n\n"
            "Выбери свою роль:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
        )
        await state.update_data(current_detail_field="role", current_game_key=first_game)
        return

    # Toggle game selection
    game_key = None
    for k, v in GAMES.items():
        if text == f"🎮 {v['name']}":
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
            row.append(KeyboardButton(text=f"{prefix}🎮 {GAMES[gk]['name']}"))
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
                row.append(KeyboardButton(text=f"{prefix}🎮 {GAMES[gk]['name']}"))
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
        buttons.append([KeyboardButton(text="⬅ Назад")])
        await message.answer(
            f"✅ Роль: <b>{text}</b>\n\n"
            "Выбери свой ранг:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
        )
        return

    if field == "rank":
        if text not in game_data["ranks"]:
            await message.answer("❌ Выбери ранг кнопкой:")
            return
        details[game_key]["rank"] = text
        await state.update_data(game_details=details)

        # Сохраняем в БД
        await db.upsert_game_profile(
            message.from_user.id, game_data["name"], text, details[game_key].get("role", "")
        )

        # Следующая игра или дальше
        selected = data.get("selected_games", [])
        idx = data.get("current_game_idx", 0) + 1

        if idx < len(selected):
            next_game = selected[idx]
            next_data = GAMES[next_game]
            await state.update_data(current_game_idx=idx, current_game_key=next_game, current_detail_field="role")
            buttons = [[KeyboardButton(text=r)] for r in next_data["roles"]]
            buttons.append([KeyboardButton(text="⬅ Назад")])
            await message.answer(
                f"✅ Ранг сохранён!\n\n"
                f"🎯 Теперь <b>{next_data['name']}</b>\n"
                "Выбери свою роль:",
                parse_mode="HTML",
                reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
            )
        else:
            # Все игры пройдены — шаг 6: стиль игры
            await state.set_state(Form.play_style)
            await state.update_data(selected_styles=[])
            buttons = [[KeyboardButton(text=s)] for s in PLAY_STYLES]
            buttons.append([KeyboardButton(text="✅ Далее")])
            buttons.append([KeyboardButton(text="⬅ Назад")])
            await message.answer(
                "🔥 <b>Шаг 6/8</b> · Как ты играешь?\n\n"
                "Выбери до 3 стилей, потом «✅ Далее»:",
                parse_mode="HTML",
                reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
            )


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
            "🎤 <b>Шаг 7/8</b> · Готов voice-чатить?\n\n"
            "Выбери вариант:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True),
        )
        return

    # Toggle style
    styles = data.get("selected_styles", [])
    if text in styles:
        styles.remove(text)
    elif len(styles) < 3:
        styles.append(text)
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

    # Шаг 8: О себе
    await state.set_state(Form.bio)
    await message.answer(
        f"✅ Микро: <b>{text}</b>\n\n"
        "📝 <b>Шаг 8/8</b> · Расскажи о себе (необязательно):\n\n"
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
        await message.answer("Назад к микрофону:", reply_markup=ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
        return

    bio = "" if text == "✅ Сохранить" else text[:500]
    await db.update_user(message.from_user.id, bio=bio)

    # Завершение анкеты
    user = await db.get_user(message.from_user.id)
    games = await db.get_user_games(message.from_user.id)
    await state.clear()

    games_text = ", ".join([f"{g['game_name']} ({g['rank']})" for g in games]) or "не указано"
    gender_text = GENDER_OPTIONS.get(user.get("gender", "hidden"), "🤔 Не указывать")
    mic_text = MIC_OPTIONS.get(user.get("mic_status", "no_mic"), "🔇 Нет микрофона")

    await message.answer(
        f"🎉 <b>Анкета готова!</b>\n\n"
        f"🎮 <b>{user['nickname']}</b>\n"
        f"📅 {user['age_group']} · {gender_text}\n"
        f"🎯 {games_text}\n"
        f"🎤 {mic_text}\n"
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
        lines = f"  🎯 {g['game_name']} · {g['rank']}"
        if g.get("role"):
            lines += f" · {g['role']}"
        games_lines.append(lines)
    games_text = "\n".join(games_lines) if games_lines else "  не указано"

    bio_text = user.get("bio", "")
    bio_section = f"\n💬 <i>\"{bio_text[:200]}\"</i>" if bio_text else ""

    card = (
        f"🎮 <b>{user['nickname']}</b>\n"
        f"📅 {user['age_group']} · {gender_text}\n\n"
        f"{games_text}\n\n"
        f"🎤 {mic_text}{bio_section}"
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
            f"Вы и <b>{name}</b> оба хотят играть вместе!\n"
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
            f"Вы и <b>{name}</b> оба хотят играть вместе!\n"
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
    games_text = ", ".join([f"{g['game_name']} ({g['rank']})" for g in games]) or "нет"

    text = (
        f"👤 <b>Мой профиль</b>\n\n"
        f"🎮 <b>{user['nickname']}</b>\n"
        f"📅 {user['age_group']} · {gender_text}\n"
        f"🎯 {games_text}\n"
        f"🎤 {mic_text}\n"
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
        "4. Не OMITNSWAM\n"
        "5. Жалуйся на нарушителей — мы разберёмся\n\n"
        "При 3+ жалобах — автоматический бан 🚫"
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
