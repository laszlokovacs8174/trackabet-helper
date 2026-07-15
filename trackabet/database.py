"""Local SQLite database for bet storage."""
import sqlite3
from datetime import datetime, timezone
from typing import Optional
from .config import get_db_path


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS bets (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            event           TEXT NOT NULL,
            sport           TEXT NOT NULL DEFAULT 'other',
            market_type     TEXT NOT NULL DEFAULT 'moneyline',
            selection       TEXT NOT NULL,
            odds            REAL NOT NULL,
            stake           REAL NOT NULL,
            bookmaker       TEXT NOT NULL DEFAULT 'bet365',
            tipster         TEXT DEFAULT '',
            notes           TEXT DEFAULT '',
            status          TEXT NOT NULL DEFAULT 'pending',
            profit          REAL DEFAULT 0,
            clv             REAL DEFAULT 0,
            trackabet_id    TEXT DEFAULT '',
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            settled_at      TEXT
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            email           TEXT NOT NULL,
            token           TEXT DEFAULT '',
            logged_in_at    TEXT NOT NULL DEFAULT (datetime('now')),
            last_active     TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_bets_created ON bets(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_bets_status ON bets(status);
        CREATE INDEX IF NOT EXISTS idx_bets_sport ON bets(sport);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_bets_trackabet_id ON bets(trackabet_id);
    """)


def add_bet(bet: dict) -> int:
    market_type = bet.get("market_type") or "moneyline"
    conn = get_conn()
    cursor = conn.execute("""
        INSERT INTO bets (event, sport, market_type, selection, odds, stake,
                          bookmaker, tipster, notes, status, profit, clv,
                          trackabet_id, created_at, settled_at)
        VALUES (:event, :sport, :market_type, :selection, :odds, :stake,
                :bookmaker, :tipster, :notes, :status, :profit, :clv,
                :trackabet_id, :created_at, :settled_at)
    """, {
        "event": bet["event"],
        "sport": bet.get("sport", "other"),
        "market_type": market_type,
        "selection": bet["selection"],
        "odds": bet["odds"],
        "stake": bet["stake"],
        "bookmaker": bet.get("bookmaker", "bet365"),
        "tipster": bet.get("tipster", ""),
        "notes": bet.get("notes", ""),
        "status": bet.get("status", "pending"),
        "profit": bet.get("profit", 0),
        "clv": bet.get("clv", 0),
        "trackabet_id": bet.get("trackabet_id", ""),
        "created_at": bet.get("created_at", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
        "settled_at": bet.get("settled_at"),
    })
    conn.commit()
    bet_id = cursor.lastrowid
    conn.close()
    return bet_id


def get_recent_bets(limit: int = 20, sport: Optional[str] = None) -> list[dict]:
    conn = get_conn()
    if sport:
        rows = conn.execute(
            "SELECT * FROM bets WHERE sport = ? ORDER BY created_at DESC LIMIT ?",
            (sport, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM bets ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_bet(bet_id: int) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM bets WHERE id = ?", (bet_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_bet(bet_id: int, **kwargs):
    if not kwargs:
        return
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [bet_id]
    conn = get_conn()
    conn.execute(f"UPDATE bets SET {sets} WHERE id = ?", vals)
    conn.commit()
    conn.close()


def get_stats() -> dict:
    conn = get_conn()
    stats = conn.execute("""
        SELECT
            COUNT(*) as total_bets,
            COALESCE(SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END), 0) as wins,
            COALESCE(SUM(CASE WHEN status = 'lost' THEN 1 ELSE 0 END), 0) as losses,
            COALESCE(SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END), 0) as pending,
            COALESCE(SUM(stake), 0) as total_staked,
            COALESCE(SUM(profit), 0) as total_profit,
            COALESCE(AVG(CASE WHEN status IN ('won', 'lost') THEN odds ELSE NULL END), 0) as avg_odds,
            COALESCE(AVG(CASE WHEN status IN ('won', 'lost') THEN stake ELSE NULL END), 0) as avg_stake
        FROM bets
    """).fetchone()
    conn.close()
    return dict(stats)


def clear_session():
    conn = get_conn()
    conn.execute("DELETE FROM sessions")
    conn.commit()
    conn.close()


def set_session_email(email: str):
    conn = get_conn()
    conn.execute("DELETE FROM sessions")
    conn.execute("INSERT INTO sessions (email) VALUES (?)", (email,))
    conn.commit()
    conn.close()


def get_session_email() -> Optional[str]:
    conn = get_conn()
    row = conn.execute(
        "SELECT email FROM sessions ORDER BY logged_in_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return row["email"] if row else None
