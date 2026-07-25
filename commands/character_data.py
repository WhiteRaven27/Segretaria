import sqlite3
import discord
import uuid
import os
import asyncio
import re

DB_PATH = "data/characters.db"

CHARACTER_ID_REGEX = re.compile(r"^[a-f0-9]{8}$", re.IGNORECASE)

_edit_locks = {}


def _get_connection() -> sqlite3.Connection:
    """Get a connection to the SQLite database (thread-safe)."""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _init_db():
    """Create tables if they don't exist."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                user_id      TEXT NOT NULL,
                character_id TEXT NOT NULL,
                nome         TEXT DEFAULT '',
                identita     TEXT DEFAULT '',
                origine      TEXT DEFAULT '',
                tema         TEXT DEFAULT '',
                descrizione  TEXT DEFAULT '',
                livello      TEXT DEFAULT '',
                classe       TEXT DEFAULT '',
                abilita      TEXT DEFAULT '',
                link         TEXT DEFAULT '',
                immagine     TEXT DEFAULT NULL,
                hex_color    TEXT DEFAULT '#5865F2',
                PRIMARY KEY (user_id, character_id)
            )
        """)
        # Migrazione per database esistenti senza colonna livello
        try:
            conn.execute("ALTER TABLE characters ADD COLUMN livello TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # Colonna già esistente — ignoriamo
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gallery_config (
                guild_id   TEXT PRIMARY KEY,
                channel_id INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS message_owners (
                message_id INTEGER PRIMARY KEY,
                user_id    INTEGER NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


# Initialize DB at module load
_init_db()


def validate_character_id(character_id: str) -> bool:
    if not character_id or not isinstance(character_id, str):
        return False
    return CHARACTER_ID_REGEX.match(character_id) is not None


class CharacterData:
    def __init__(self, character_id=None):
        self.character_id = character_id or str(uuid.uuid4())[:8]
        self.nome = "Non impostato"
        self.identita = "Non impostata"
        self.origine = "Non impostata"
        self.tema = "Non impostato"
        self.descrizione = "Non impostata"
        self.livello = ""
        self.classe = "Non impostata"
        self.abilita = ""
        self.link = ""
        self.immagine = None
        self.hex_color = "#5865F2"


def _row_to_obj(row: sqlite3.Row) -> CharacterData:
    obj = CharacterData(character_id=row["character_id"])
    for key in ("nome", "identita", "origine", "tema", "descrizione",
                "livello", "classe", "abilita", "link", "immagine", "hex_color"):
        setattr(obj, key, row[key])
    return obj


def create_embed(data: CharacterData) -> discord.Embed:
    try:
        color = discord.Color.from_str(data.hex_color)
    except:
        color = discord.Color.blurple()

    # Tronca i campi ai limiti ufficiali di Discord per evitare 400 Bad Request
    title = (data.nome or "")[:256]

    # Se non c'è descrizione, non mostrarla nell'embed
    descrizione_raw = (data.descrizione or "").strip()
    if descrizione_raw and descrizione_raw != "Non impostata":
        description = descrizione_raw[:4096]
    else:
        description = None

    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )

    embed.add_field(name="Identità", value=(data.identita or "—")[:1024], inline=True)
    embed.add_field(name="Origine", value=(data.origine or "—")[:1024], inline=True)
    embed.add_field(name="Tema", value=(data.tema or "—")[:1024], inline=True)
    embed.add_field(name="Livello", value=(data.livello or "—")[:1024], inline=True)
    embed.add_field(name="Classe", value=(data.classe or "—")[:1024], inline=True)

    if data.abilita:
        abilita_text = (data.abilita or "")[:1024]
        embed.add_field(name="Eroiche", value=abilita_text, inline=False)

    if data.link:
        embed.add_field(name="Scheda", value=(data.link or "")[:1024], inline=False)

    if data.immagine:
        embed.set_image(url=data.immagine)

    embed.set_footer(text="Messaggio offerto da Vanguard Express")
    return embed


def get_edit_lock(user_id):
    uid = str(user_id)
    if uid not in _edit_locks:
        _edit_locks[uid] = asyncio.Lock()
    return _edit_locks[uid]


async def read_all() -> dict:
    """Return full data as nested dict (for backward compat with scheda.py)."""
    def _read():
        conn = _get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM characters ORDER BY user_id, character_id"
            ).fetchall()
            data = {}
            for row in rows:
                uid = row["user_id"]
                if uid not in data:
                    data[uid] = {}
                data[uid][row["character_id"]] = {
                    "character_id": row["character_id"],
                    "nome": row["nome"],
                    "identita": row["identita"],
                    "origine": row["origine"],
                    "tema": row["tema"],
                    "descrizione": row["descrizione"],
                    "livello": row["livello"],
                    "classe": row["classe"],
                    "abilita": row["abilita"],
                    "link": row["link"],
                    "immagine": row["immagine"],
                    "hex_color": row["hex_color"],
                }
            return data
        finally:
            conn.close()
    return await asyncio.to_thread(_read)


async def load_character(user_id, character_id=None) -> CharacterData | None:
    def _load():
        conn = _get_connection()
        try:
            uid = str(user_id)
            if character_id:
                if not validate_character_id(character_id):
                    return None
                row = conn.execute(
                    "SELECT * FROM characters WHERE user_id = ? AND character_id = ?",
                    (uid, character_id)
                ).fetchone()
                return _row_to_obj(row) if row else None
            else:
                row = conn.execute(
                    "SELECT * FROM characters WHERE user_id = ? ORDER BY rowid LIMIT 1",
                    (uid,)
                ).fetchone()
                return _row_to_obj(row) if row else None
        finally:
            conn.close()
    return await asyncio.to_thread(_load)


async def load_all_characters(user_id) -> list[CharacterData]:
    def _load_all():
        conn = _get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM characters WHERE user_id = ? ORDER BY nome",
                (str(user_id),)
            ).fetchall()
            return [_row_to_obj(r) for r in rows]
        finally:
            conn.close()
    return await asyncio.to_thread(_load_all)


async def save_character(user_id, obj: CharacterData):
    lock = get_edit_lock(user_id)
    async with lock:
        def _save():
            conn = _get_connection()
            try:
                if not validate_character_id(obj.character_id):
                    raise ValueError(f"Invalid character ID: {obj.character_id}")

                conn.execute("""
                    INSERT OR REPLACE INTO characters
                        (user_id, character_id, nome, identita, origine, tema,
                         descrizione, livello, classe, abilita, link, immagine, hex_color)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(user_id), obj.character_id,
                    obj.nome, obj.identita, obj.origine, obj.tema,
                    obj.descrizione, obj.livello, obj.classe, obj.abilita,
                    obj.link, obj.immagine, obj.hex_color,
                ))
                conn.commit()
            finally:
                conn.close()

        await asyncio.to_thread(_save)


async def delete_character(user_id, character_id=None) -> bool:
    lock = get_edit_lock(user_id)
    async with lock:
        def _delete():
            conn = _get_connection()
            try:
                uid = str(user_id)
                if character_id:
                    if not validate_character_id(character_id):
                        return False
                    cursor = conn.execute(
                        "DELETE FROM characters WHERE user_id = ? AND character_id = ?",
                        (uid, character_id)
                    )
                else:
                    cursor = conn.execute(
                        "DELETE FROM characters WHERE user_id = ? AND rowid IN ("
                        "SELECT rowid FROM characters WHERE user_id = ? LIMIT 1)",
                        (uid, uid)
                    )
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

        return await asyncio.to_thread(_delete)


# ─── Gallery config ───────────────────────────────────────

async def get_gallery_channel(guild_id) -> int | None:
    def _get():
        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT channel_id FROM gallery_config WHERE guild_id = ?",
                (str(guild_id),)
            ).fetchone()
            return row["channel_id"] if row else None
        finally:
            conn.close()
    return await asyncio.to_thread(_get)


async def set_gallery_channel(guild_id, channel_id: int):
    def _set():
        conn = _get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO gallery_config (guild_id, channel_id)
                VALUES (?, ?)
            """, (str(guild_id), channel_id))
            conn.commit()
        finally:
            conn.close()
    await asyncio.to_thread(_set)


# ─── Message owners ──────────────────────────────────────

def load_message_owners() -> dict[int, int]:
    """Sync — only called once at startup before the event loop is busy."""
    conn = _get_connection()
    try:
        rows = conn.execute("SELECT message_id, user_id FROM message_owners").fetchall()
        return {row["message_id"]: row["user_id"] for row in rows}
    finally:
        conn.close()


async def save_message_owners(data: dict[int, int]):
    """Save message_owners: insert/update existing entries,
    and REMOVE those no longer in the dictionary."""
    def _save():
        conn = _get_connection()
        try:
            existing = conn.execute("SELECT message_id FROM message_owners").fetchall()
            current_ids = set(data.keys())
            for row in existing:
                if row["message_id"] not in current_ids:
                    conn.execute("DELETE FROM message_owners WHERE message_id = ?", (row["message_id"],))

            conn.executemany(
                "INSERT OR REPLACE INTO message_owners (message_id, user_id) VALUES (?, ?)",
                [(mid, uid) for mid, uid in list(data.items())]
            )
            conn.commit()
        finally:
            conn.close()
    await asyncio.to_thread(_save)


async def delete_message_owner(message_id: int):
    """Remove a single message_owner from the database."""
    def _delete():
        conn = _get_connection()
        try:
            conn.execute("DELETE FROM message_owners WHERE message_id = ?", (message_id,))
            conn.commit()
        finally:
            conn.close()
    await asyncio.to_thread(_delete)
