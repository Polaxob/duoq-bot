"""
DuoQ — База данных (SQLite + aiosqlite)
"""

import aiosqlite
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "duoq.db"


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    return db


async def init_db():
    db = await get_db()
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            nickname TEXT NOT NULL,
            name TEXT NOT NULL DEFAULT '',
            age_group TEXT NOT NULL,
            gender TEXT NOT NULL DEFAULT 'hidden',
            mic_status TEXT NOT NULL DEFAULT 'no_mic',
            languages TEXT NOT NULL DEFAULT '["ru"]',
            play_style TEXT DEFAULT '[]',
            rating TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS game_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            game_name TEXT NOT NULL,
            rank TEXT DEFAULT '',
            role TEXT DEFAULT '',
            extra_fields TEXT DEFAULT '{}',
            FOREIGN KEY (user_id) REFERENCES users(telegram_id),
            UNIQUE(user_id, game_name)
        );

        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user_id INTEGER NOT NULL,
            to_user_id INTEGER NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('like', 'skip', 'fav')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_user_id) REFERENCES users(telegram_id),
            FOREIGN KEY (to_user_id) REFERENCES users(telegram_id),
            UNIQUE(from_user_id, to_user_id)
        );

        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_a_id INTEGER NOT NULL,
            user_b_id INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_a_id) REFERENCES users(telegram_id),
            FOREIGN KEY (user_b_id) REFERENCES users(telegram_id),
            UNIQUE(user_a_id, user_b_id)
        );

        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER NOT NULL,
            reported_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (reporter_id) REFERENCES users(telegram_id),
            FOREIGN KEY (reported_id) REFERENCES users(telegram_id)
        );

        CREATE TABLE IF NOT EXISTS started_users (
            telegram_id INTEGER PRIMARY KEY,
            first_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    await db.commit()
    # Миграция: добавить play_style если нет
    try:
        await db.execute("ALTER TABLE users ADD COLUMN play_style TEXT DEFAULT '[]'")
        await db.commit()
    except Exception:
        pass  # колонка уже есть
    # Миграция: добавить rating если нет
    try:
        await db.execute("ALTER TABLE users ADD COLUMN rating TEXT DEFAULT ''")
        await db.commit()
    except Exception:
        pass  # колонка уже есть
    # Миграция: добавить name если нет
    try:
        await db.execute("ALTER TABLE users ADD COLUMN name TEXT DEFAULT ''")
        await db.commit()
    except Exception:
        pass  # колонка уже есть
    await db.close()


# ---- User operations ----

async def create_user(telegram_id: int, nickname: str, name: str, age_group: str, gender: str):
    db = await get_db()
    await db.execute(
        "INSERT OR REPLACE INTO users (telegram_id, nickname, name, age_group, gender) VALUES (?, ?, ?, ?, ?)",
        (telegram_id, nickname, name, age_group, gender),
    )
    await db.commit()
    await db.close()


async def update_user(telegram_id: int, **fields):
    if not fields:
        return
    db = await get_db()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [telegram_id]
    await db.execute(f"UPDATE users SET {set_clause} WHERE telegram_id = ?", values)
    await db.commit()
    await db.close()


async def get_user(telegram_id: int):
    db = await get_db()
    cursor = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def get_user_games(telegram_id: int):
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM game_profiles WHERE user_id = ?", (telegram_id,)
    )
    rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]


async def upsert_game_profile(user_id: int, game_name: str, rank: str, role: str, extra: dict = None):
    db = await get_db()
    await db.execute(
        """INSERT INTO game_profiles (user_id, game_name, rank, role, extra_fields)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(user_id, game_name)
           DO UPDATE SET rank=?, role=?, extra_fields=?""",
        (user_id, game_name, rank, role, json.dumps(extra or {}), rank, role, json.dumps(extra or {})),
    )
    await db.commit()
    await db.close()


# ---- Action operations ----

async def save_action(from_id: int, to_id: int, action: str):
    db = await get_db()
    await db.execute(
        "INSERT OR REPLACE INTO actions (from_user_id, to_user_id, action) VALUES (?, ?, ?)",
        (from_id, to_id, action),
    )
    await db.commit()
    await db.close()


async def check_mutual_like(user_a: int, user_b: int) -> bool:
    db = await get_db()
    cursor = await db.execute(
        """SELECT COUNT(*) FROM actions
           WHERE action IN ('like','fav')
             AND (
               (from_user_id = ? AND to_user_id = ?)
               OR
               (from_user_id = ? AND to_user_id = ?)
             )""",
        (user_a, user_b, user_b, user_a),
    )
    row = await cursor.fetchone()
    await db.close()
    return row[0] >= 2


async def create_match(user_a: int, user_b: int):
    db = await get_db()
    a, b = min(user_a, user_b), max(user_a, user_b)
    await db.execute(
        "INSERT OR IGNORE INTO matches (user_a_id, user_b_id) VALUES (?, ?)",
        (a, b),
    )
    await db.commit()
    await db.close()


async def get_matches(user_id: int):
    db = await get_db()
    cursor = await db.execute(
        """SELECT * FROM matches
           WHERE (user_a_id = ? OR user_b_id = ?) AND is_active = 1""",
        (user_id, user_id),
    )
    rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]


# ---- Search helpers ----

async def get_active_profiles(exclude_id: int, game: str = None):
    db = await get_db()
    if game:
        cursor = await db.execute(
            """SELECT u.* FROM users u
               JOIN game_profiles gp ON u.telegram_id = gp.user_id
               WHERE u.telegram_id != ? AND u.is_active = 1 AND gp.game_name = ?
               ORDER BY RANDOM()""",
            (exclude_id, game),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_id != ? AND is_active = 1 ORDER BY RANDOM()",
            (exclude_id,),
        )
    rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]


async def get_user_favorites(user_id: int):
    db = await get_db()
    cursor = await db.execute(
        "SELECT to_user_id FROM actions WHERE from_user_id = ? AND action = 'fav'",
        (user_id,),
    )
    rows = await cursor.fetchall()
    await db.close()
    return [r[0] for r in rows]


async def get_user_action_stats(user_id: int) -> dict:
    """Сколько раз пользователю поставили «Понравилось» и «Не понравилось»."""
    db = await get_db()
    likes = 0
    dislikes = 0
    cursor = await db.execute(
        "SELECT action, COUNT(*) AS cnt FROM actions WHERE to_user_id = ? GROUP BY action",
        (user_id,),
    )
    for r in await cursor.fetchall():
        if r["action"] in ("like", "fav"):
            likes += r["cnt"]
        elif r["action"] == "skip":
            dislikes += r["cnt"]
    await db.close()
    return {"likes": likes, "dislikes": dislikes}


async def remove_game_profile(user_id: int, game_name: str):
    """Удалить профиль конкретной игры."""
    db = await get_db()
    await db.execute(
        "DELETE FROM game_profiles WHERE user_id = ? AND game_name = ?",
        (user_id, game_name),
    )
    await db.commit()
    await db.close()


async def get_seen_ids(user_id: int):
    db = await get_db()
    cursor = await db.execute(
        "SELECT to_user_id FROM actions WHERE from_user_id = ?",
        (user_id,),
    )
    rows = await cursor.fetchall()
    await db.close()
    return {r[0] for r in rows}


# ---- Profile expiry (3 days) ----

PROFILE_LIFETIME_DAYS = 3


async def cleanup_expired_profiles():
    """Удалить анкеты старше 3 дней."""
    db = await get_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=PROFILE_LIFETIME_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    # Удалить game_profiles протухших пользователей
    await db.execute(
        """DELETE FROM game_profiles WHERE user_id IN
           (SELECT telegram_id FROM users WHERE created_at < ?)""",
        (cutoff,),
    )
    # Удалить сами анкеты
    cursor = await db.execute(
        "DELETE FROM users WHERE created_at < ? RETURNING telegram_id, nickname",
        (cutoff,),
    )
    deleted = await cursor.fetchall()
    await db.commit()
    await db.close()
    return [dict(r) for r in deleted]


async def get_profile_expiry(telegram_id: int) -> dict:
    """Получить дату создания и срок истечения анкеты."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT created_at FROM users WHERE telegram_id = ?",
        (telegram_id,),
    )
    row = await cursor.fetchone()
    await db.close()
    if not row:
        return None
    created = row[0]
    if isinstance(created, str):
        created = datetime.strptime(created, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    expires = created + timedelta(days=PROFILE_LIFETIME_DAYS)
    now = datetime.now(timezone.utc)
    days_left = max(0, (expires - now).days)
    hours_left = max(0, int((expires - now).total_seconds() // 3600))
    return {
        "created_at": created,
        "expires_at": expires,
        "days_left": days_left,
        "hours_left": hours_left,
    }


# ---- Stats / admin ----

async def record_start(telegram_id: int):
    """Записать, что пользователь зашёл в бота (только первый раз)."""
    db = await get_db()
    await db.execute(
        "INSERT OR IGNORE INTO started_users (telegram_id) VALUES (?)",
        (telegram_id,),
    )
    await db.commit()
    await db.close()


async def get_stats() -> dict:
    """Статистика для админа."""
    db = await get_db()
    cursor = await db.execute("SELECT COUNT(*) FROM started_users")
    total_started = (await cursor.fetchone())[0]

    cursor = await db.execute("SELECT COUNT(*) FROM users")
    total_profiles = (await cursor.fetchone())[0]

    cursor = await db.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
    active_profiles = (await cursor.fetchone())[0]

    cursor = await db.execute("SELECT COUNT(*) FROM matches")
    total_matches = (await cursor.fetchone())[0]

    # Анкеты за сегодня и за 7 дней
    cursor = await db.execute(
        "SELECT COUNT(*) FROM users WHERE date(created_at) = date('now')"
    )
    new_today = (await cursor.fetchone())[0]
    cursor = await db.execute(
        "SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', '-7 days')"
    )
    new_7d = (await cursor.fetchone())[0]

    # Разбивка по играм (активные)
    cursor = await db.execute(
        """SELECT gp.game_name, COUNT(DISTINCT gp.user_id) AS cnt
           FROM game_profiles gp
           JOIN users u ON u.telegram_id = gp.user_id AND u.is_active = 1
           GROUP BY gp.game_name
           ORDER BY cnt DESC"""
    )
    games = {r["game_name"]: r["cnt"] for r in await cursor.fetchall()}

    await db.close()
    return {
        "total_started": total_started,
        "total_profiles": total_profiles,
        "active_profiles": active_profiles,
        "total_matches": total_matches,
        "new_today": new_today,
        "new_7d": new_7d,
        "games": games,
    }
