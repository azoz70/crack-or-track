"""SQLite persistence for players, progress, and activity."""

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "game.db"


def connect():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                xp INTEGER NOT NULL DEFAULT 0,
                created TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS progress (
                player_id INTEGER NOT NULL,
                mission_id TEXT NOT NULL,
                best_score INTEGER NOT NULL DEFAULT 0,
                attempts INTEGER NOT NULL DEFAULT 0,
                completed_at TEXT,
                PRIMARY KEY (player_id, mission_id)
            );
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                mission_id TEXT NOT NULL,
                score INTEGER NOT NULL,
                xp INTEGER NOT NULL,
                created TEXT NOT NULL
            );
            """
        )
        row = conn.execute("SELECT id FROM players ORDER BY id LIMIT 1").fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO players (name, xp, created) VALUES (?, 0, ?)",
                ("Operator", datetime.now().isoformat(timespec="seconds")),
            )


def player():
    with connect() as conn:
        return conn.execute("SELECT * FROM players ORDER BY id LIMIT 1").fetchone()


def progress_map(player_id):
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM progress WHERE player_id = ?", (player_id,)
        ).fetchall()
        return {r["mission_id"]: dict(r) for r in rows}


def save_attempt(player_id, mission_id, score, xp):
    now = datetime.now().isoformat(timespec="seconds")
    with connect() as conn:
        conn.execute(
            "UPDATE players SET xp = xp + ? WHERE id = ?", (xp, player_id)
        )
        row = conn.execute(
            "SELECT * FROM progress WHERE player_id = ? AND mission_id = ?",
            (player_id, mission_id),
        ).fetchone()
        if row:
            conn.execute(
                """UPDATE progress SET best_score = MAX(best_score, ?),
                   attempts = attempts + 1, completed_at = ?
                   WHERE player_id = ? AND mission_id = ?""",
                (score, now, player_id, mission_id),
            )
        else:
            conn.execute(
                """INSERT INTO progress (player_id, mission_id, best_score,
                   attempts, completed_at) VALUES (?, ?, ?, 1, ?)""",
                (player_id, mission_id, score, now),
            )
        conn.execute(
            """INSERT INTO activity (player_id, mission_id, score, xp, created)
               VALUES (?, ?, ?, ?, ?)""",
            (player_id, mission_id, score, xp, now),
        )


def recent_activity(player_id, limit=8):
    with connect() as conn:
        return conn.execute(
            """SELECT * FROM activity WHERE player_id = ?
               ORDER BY id DESC LIMIT ?""",
            (player_id, limit),
        ).fetchall()


def achievements(player_id, missions):
    prog = progress_map(player_id)
    done = {mid for mid, p in prog.items() if p["attempts"] > 0}
    red = {m["id"] for m in missions if m["track"] == "red"}
    blue = {m["id"] for m in missions if m["track"] == "blue"}
    best = max((p["best_score"] for p in prog.values()), default=0)

    out = []
    out.append(("First Contact", "Complete your first mission", bool(done)))
    out.append(("Red Operator", "Complete every Red Team mission", red and red <= done))
    out.append(("Blue Team", "Complete every SOC mission", blue and blue <= done))
    out.append(("Perfectionist", "Score 100 in one mission", best >= 100))
    out.append(("Field Veteran", "Complete 5 missions", len(done) >= 5))
    out.append(("Crossover", "Complete the Red vs SOC scenario", "x1" in done))
    return out
