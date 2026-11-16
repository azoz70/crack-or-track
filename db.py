"""SQLite persistence for players, progress, activity, attempts, and reports."""

import json
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
            CREATE TABLE IF NOT EXISTS question_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                mission_id TEXT NOT NULL,
                stage_index INTEGER NOT NULL,
                stage_type TEXT NOT NULL,
                skill TEXT NOT NULL DEFAULT '',
                selected TEXT NOT NULL DEFAULT '',
                correct INTEGER NOT NULL DEFAULT 0,
                points REAL NOT NULL DEFAULT 0,
                hint_used INTEGER NOT NULL DEFAULT 0,
                created TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS xp_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                reason TEXT NOT NULL,
                mission_id TEXT,
                created TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS mission_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                mission_id TEXT NOT NULL,
                data TEXT NOT NULL,
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


def get_mission_progress(player_id, mission_id):
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM progress WHERE player_id = ? AND mission_id = ?",
            (player_id, mission_id),
        ).fetchone()


def save_attempt(player_id, mission_id, score, xp_delta):
    """Record a completed mission. `xp_delta` is the XP to actually award
    (already de-duplicated by the caller), so replays never double-count XP."""
    now = datetime.now().isoformat(timespec="seconds")
    with connect() as conn:
        if xp_delta:
            conn.execute(
                "UPDATE players SET xp = xp + ? WHERE id = ?", (xp_delta, player_id)
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
            (player_id, mission_id, score, xp_delta, now),
        )
        if xp_delta:
            conn.execute(
                """INSERT INTO xp_ledger (player_id, amount, reason, mission_id, created)
                   VALUES (?, ?, 'mission', ?, ?)""",
                (player_id, xp_delta, mission_id, now),
            )


def record_question_attempt(player_id, mission_id, stage_index, stage_type,
                            skill, selected, correct, points, hint_used):
    with connect() as conn:
        conn.execute(
            """INSERT INTO question_attempts
               (player_id, mission_id, stage_index, stage_type, skill,
                selected, correct, points, hint_used, created)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (player_id, mission_id, stage_index, stage_type, skill or "",
             selected, 1 if correct else 0, points, hint_used or 0,
             datetime.now().isoformat(timespec="seconds")),
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


def skill_stats(player_id):
    """Aggregate correct/total per skill from recorded question attempts."""
    with connect() as conn:
        rows = conn.execute(
            """SELECT skill, COUNT(*) AS total, SUM(correct) AS correct
               FROM question_attempts WHERE player_id = ? AND skill != ''
               GROUP BY skill""",
            (player_id,),
        ).fetchall()
        return {r["skill"]: {"total": r["total"], "correct": r["correct"] or 0} for r in rows}


def question_history(player_id, mission_id=None, incorrect_only=False, limit=200):
    with connect() as conn:
        q = "SELECT * FROM question_attempts WHERE player_id = ?"
        args = [player_id]
        if mission_id:
            q += " AND mission_id = ?"
            args.append(mission_id)
        if incorrect_only:
            q += " AND correct = 0"
        q += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        return conn.execute(q, args).fetchall()


def save_mission_report(player_id, mission_id, data):
    with connect() as conn:
        conn.execute(
            "INSERT INTO mission_reports (player_id, mission_id, data, created) VALUES (?, ?, ?, ?)",
            (player_id, mission_id, json.dumps(data), datetime.now().isoformat(timespec="seconds")),
        )


def recent_reports(player_id, limit=10):
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM mission_reports WHERE player_id = ? ORDER BY id DESC LIMIT ?",
            (player_id, limit),
        ).fetchall()


def get_report(report_id):
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM mission_reports WHERE id = ?", (report_id,)
        ).fetchone()
