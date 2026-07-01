import json
import discord
import uuid
import os
import asyncio
import re

DATA_PATH = "data/characters.json"

# Character ID validation regex (8 hex chars)
CHARACTER_ID_REGEX = re.compile(r"^[a-f0-9]{8}$", re.IGNORECASE)

# Lock for concurrent edit prevention (user_id -> asyncio.Lock)
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
    with open(DATA_PATH, "w") as f:
        json.dump(data, f, indent=4)


def get_edit_lock(user_id):
    """Get or create an asyncio lock for a user to prevent concurrent edits"""
    uid = str(user_id)
    if uid not in _edit_locks:
        _edit_locks[uid] = asyncio.Lock()
    return _edit_locks[uid]


def validate_character_id(character_id):
    """Validate character ID format and length"""
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
        self.classe = "Non impostata"
        self.abilita = ""  # EROICHE
        self.link = ""
        self.immagine = None
        self.hex_color = "#5865F2"


def create_embed(data: CharacterData):
    try:
        color = discord.Color.from_str(data.hex_color)
    except:
        color = discord.Color.blurple()

    embed = discord.Embed(
        title=data.nome,
        description=data.descrizione,
        color=color
    )

    embed.add_field(name="Identità", value=data.identita, inline=True)
    embed.add_field(name="Origine", value=data.origine, inline=True)
    embed.add_field(name="Tema", value=data.tema, inline=True)
    embed.add_field(name="Classe", value=data.classe, inline=True)

    if data.abilita:
        embed.add_field(name="Eroiche", value=data.abilita, inline=False)

    if data.link:
        embed.add_field(name="Link Scheda", value=data.link, inline=False)

    if data.immagine:
        embed.set_image(url=data.immagine)

    embed.set_footer(text="Messaggio offerto da Vanguard Express")
    return embed


def load_character(user_id, character_id=None):
    data = read_all()
    user_chars = data.get(str(user_id), {})

    if not user_chars:
        return None

    if character_id:
        # Validate character ID
        if not validate_character_id(character_id):
            return None
        
        raw = user_chars.get(character_id)
        if not raw:
            return None
        return _to_obj(character_id, raw)

    first_id = next(iter(user_chars))
    return _to_obj(first_id, user_chars[first_id])


def load_all_characters(user_id):
    data = read_all()
    user_chars = data.get(str(user_id), {})

    return [
        _to_obj(cid, raw)
        for cid, raw in user_chars.items()
    ]


async def save_character(user_id, obj):
    """Save character with race condition protection using asyncio lock"""
    # Get lock for this user
    lock = get_edit_lock(user_id)
    
    # Acquire lock to prevent concurrent saves
    async with lock:
        data = read_all()

        uid = str(user_id)
        if uid not in data:
            data[uid] = {}

        # Validate character ID before saving
        if not validate_character_id(obj.character_id):
            raise ValueError(f"Invalid character ID: {obj.character_id}")

        data[uid][obj.character_id] = {
            "character_id": obj.character_id,
            "nome": obj.nome,
            "identita": obj.identita,
            "origine": obj.origine,
            "tema": obj.tema,
            "descrizione": obj.descrizione,
            "classe": obj.classe,
            "abilita": obj.abilita,
            "link": obj.link,
            "immagine": obj.immagine,
            "hex_color": obj.hex_color
        }

        write_all(data)


def delete_character(user_id, character_id=None):
    """Delete a character with validation"""
    data = read_all()
    uid = str(user_id)

    if uid not in data:
        return False

    if not data[uid]:
        return False

    if character_id:
        # Validate character ID
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

    write_all(data)
    return True


def _to_obj(cid, d):
    obj = CharacterData(character_id=cid)
    for k, v in d.items():
        if k != "character_id":
            setattr(obj, k, v)
    return obj
