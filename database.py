"""
DuoQ — База данных (SQLite + aiosqlite)
"""

import aiosqlite
import json
import os
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
            age_group TEXT NOT NULL,
            gender TEXT NOT NULL DEFAULT 'hidden',
            mic_status TEXT NOT NULL DEFAULT 'no_mic',
            languages TEXT NOT NULL DEFAULT '["ru"]',
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
    """)
    await db.commit()
    await db.close()


# ---- User operations ----

async def create_user(telegram_id: int, nickname: str, age_group: str, gender: str):
    db = await get_db()
    await db.execute(
        "INSERT OR REPLACE INTO users (telegram_id, nickname, age_group, gender) VALUES (?, ?, ?, ?)",
        (telegram_id, nickname, age_group, gender),
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


async def get_seen_ids(user_id: int):
    db = await get_db()
    cursor = await db.execute(
        "SELECT to_user_id FROM actions WHERE from_user_id = ?",
        (user_id,),
    )
    rows = await cursor.fetchall()
    await db.close()
    return {r[0] for r in rows}
