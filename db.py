# db.py – Operacje na bazie SQLite

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "audyty.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audyty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            firma TEXT NOT NULL,
            imie TEXT NOT NULL,
            nazwisko TEXT NOT NULL,
            stanowisko TEXT NOT NULL,
            data_zatrudnienia TEXT NOT NULL,
            pesel TEXT NOT NULL,
            status_pracownika TEXT NOT NULL,
            wymiar_etatu TEXT,
            minimalne_wynagrodzenie TEXT,
            odpowiedzi TEXT NOT NULL,
            braki_obowiazkowe INTEGER DEFAULT 0,
            braki_warunkowe INTEGER DEFAULT 0,
            braki_dobrowolne INTEGER DEFAULT 0,
            kompletnosc_procent REAL DEFAULT 100.0,
            poziom_ryzyka TEXT DEFAULT 'niskie',
            gap_list TEXT DEFAULT '[]',
            data_weryfikacji TEXT,
            weryfikujacy_imie_nazwisko TEXT,
            weryfikujacy_stanowisko TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_audyt(data: dict) -> int:
    conn = get_conn()
    cursor = conn.execute("""
        INSERT INTO audyty (
            firma, imie, nazwisko, stanowisko, data_zatrudnienia, pesel,
            status_pracownika, wymiar_etatu, minimalne_wynagrodzenie,
            odpowiedzi, braki_obowiazkowe, braki_warunkowe, braki_dobrowolne,
            kompletnosc_procent, poziom_ryzyka, gap_list,
            data_weryfikacji, weryfikujacy_imie_nazwisko, weryfikujacy_stanowisko
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data["firma"],
        data["imie"],
        data["nazwisko"],
        data["stanowisko"],
        data["data_zatrudnienia"],
        data["pesel"],
        data["status_pracownika"],
        data.get("wymiar_etatu"),
        data.get("minimalne_wynagrodzenie"),
        json.dumps(data["odpowiedzi"], ensure_ascii=False),
        data["braki_obowiazkowe"],
        data["braki_warunkowe"],
        data["braki_dobrowolne"],
        data["kompletnosc_procent"],
        data["poziom_ryzyka"],
        json.dumps(data["gap_list"], ensure_ascii=False),
        data.get("data_weryfikacji"),
        data.get("weryfikujacy_imie_nazwisko"),
        data.get("weryfikujacy_stanowisko"),
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_all_audyty() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM audyty ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        d["odpowiedzi"] = json.loads(d["odpowiedzi"])
        d["gap_list"] = json.loads(d["gap_list"])
        result.append(d)
    return result


def get_audyt_by_id(audyt_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM audyty WHERE id = ?", (audyt_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    d = dict(row)
    d["odpowiedzi"] = json.loads(d["odpowiedzi"])
    d["gap_list"] = json.loads(d["gap_list"])
    return d


def delete_audyt(audyt_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM audyty WHERE id = ?", (audyt_id,))
    conn.commit()
    conn.close()


def get_firmy() -> list[str]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT DISTINCT firma FROM audyty ORDER BY firma"
    ).fetchall()
    conn.close()
    return [r["firma"] for r in rows]


init_db()
