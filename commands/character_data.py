import json
import discord
import uuid
import os
import asyncio
import re

DATA_PATH = "data/characters.json"

CHARACTER_ID_REGEX = re.compile(r"^[a-f0-9]{8}$", re.IGNORECASE)

_edit_locks = {}


def ensure_file():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(DATA_PATH):
        with open(DATA_PATH, "w") as f:
            json.dump({}, f)


def read_all():
    ensure_file()
    try:
        with open(DATA_PATH, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def write_all(data):
    ensure_file()
    tmp = DATA_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=4)
    os.replace(tmp, DATA_PATH)  # atomic on all major OS


def get_edit_lock(user_id):
    uid = str(user_id)
    if uid not in _edit_locks:
        _edit_locks[uid] = asyncio.Lock()
    return _edit_locks[uid]


def validate_character_id(character_id):
    if not character_id or not isinstance(character_id, str):
        return False
    return CHARACTER_ID_REGEX.match(character_id) is not None


class CharacterData:
    def __init__(self, character_id=None):
        self.character_id = character_id or str(uuid.uuid4())[:8]
        self.nome      = "Non impostato"
        self.livello   = "—"
        self.identita  = "Non impostata"
        self.origine   = "Non impostata"
        self.tema      = "Non impostato"
        self.classe    = "Non impostata"
        self.abilita   = ""
        self.immagine  = None
        self.hex_color = "#5865F2"
        self.sheet_url = None


def create_embed(data: CharacterData):
    try:
        color = discord.Color.from_str(data.hex_color)
    except Exception:
        color = discord.Color.blurple()

    embed = discord.Embed(title=data.nome, color=color)

    # Field order: Identità · Origine · Tema · Livello · Classe · Abilità · Sheet
    embed.add_field(name="Identità", value=data.identita or "—", inline=True)
    embed.add_field(name="Origine",  value=data.origine  or "—", inline=True)
    embed.add_field(name="Tema",     value=data.tema     or "—", inline=True)
    embed.add_field(name="Livello",  value=getattr(data, "livello", "—") or "—", inline=True)
    embed.add_field(name="Classe",   value=data.classe   or "—", inline=False)

    abilita = getattr(data, "abilita", "")
    if abilita:
        embed.add_field(name="Abilità Eroiche", value=abilita, inline=False)

    sheet_url = getattr(data, "sheet_url", None)
    if sheet_url:
        embed.add_field(name="Foglio", value=f"[Apri il foglio]({sheet_url})", inline=False)

    if data.immagine:
        embed.set_image(url=data.immagine)

    embed.set_footer(text="Messaggio offerto da Vanguard Express")
    return embed


async def load_character(user_id, character_id=None):
    data = await asyncio.to_thread(read_all)
    user_chars = data.get(str(user_id), {})

    if not user_chars:
        return None

    if character_id:
        # Try as a character_id first (autocomplete path)
        if validate_character_id(character_id):
            raw = user_chars.get(character_id)
            if raw:
                return _to_obj(character_id, raw)

        # Fallback: match by name (manual-typing path)
        for cid, raw in user_chars.items():
            if raw.get("nome", "").lower() == character_id.lower():
                return _to_obj(cid, raw)

        return None

    first_id = next(iter(user_chars))
    return _to_obj(first_id, user_chars[first_id])


async def load_all_characters(user_id):
    data = await asyncio.to_thread(read_all)
    user_chars = data.get(str(user_id), {})

    return [
        _to_obj(cid, raw)
        for cid, raw in user_chars.items()
    ]


async def save_character(user_id, obj):
    lock = get_edit_lock(user_id)

    async with lock:
        data = await asyncio.to_thread(read_all)

        uid = str(user_id)
        if uid not in data:
            data[uid] = {}

        if not validate_character_id(obj.character_id):
            raise ValueError(f"Invalid character ID: {obj.character_id}")

        data[uid][obj.character_id] = {
            "character_id": obj.character_id,
            "nome":      obj.nome,
            "livello":   getattr(obj, "livello",   "—"),
            "identita":  obj.identita,
            "origine":   obj.origine,
            "tema":      obj.tema,
            "classe":    obj.classe,
            "abilita":   getattr(obj, "abilita",   ""),
            "immagine":  obj.immagine,
            "hex_color": obj.hex_color,
            "sheet_url": getattr(obj, "sheet_url", None),
        }

        await asyncio.to_thread(write_all, data)


async def delete_character(user_id, character_id=None):
    lock = get_edit_lock(user_id)
    async with lock:
        return await _delete_character_locked(user_id, character_id)


async def _delete_character_locked(user_id, character_id=None):
    data = await asyncio.to_thread(read_all)
    uid = str(user_id)

    if uid not in data or not data[uid]:
        return False

    if character_id:
        if not validate_character_id(character_id):
            return False

        if character_id not in data[uid]:
            return False

        del data[uid][character_id]
    else:
        first = next(iter(data[uid]))
        del data[uid][first]

    if not data[uid]:
        del data[uid]

    await asyncio.to_thread(write_all, data)
    return True


def _to_obj(cid, d):
    obj = CharacterData(character_id=cid)
    for k, v in d.items():
        if k != "character_id":
            setattr(obj, k, v)
    return obj
