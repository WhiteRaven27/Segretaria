import json
import discord
import uuid
import os

DATA_PATH = "data/characters.json"


# =========================
# FILE SAFETY
# =========================

def ensure_file():
    """Crea cartella e file se non esistono"""
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
        # file corrotto → reset sicuro
        return {}
    except FileNotFoundError:
        ensure_file()
        return {}


def write_all(data):
    ensure_file()
    with open(DATA_PATH, "w") as f:
        json.dump(data, f, indent=4)


# =========================
# DATA MODEL
# =========================

class CharacterData:
    def __init__(self, character_id=None):
        self.character_id = character_id or str(uuid.uuid4())[:8]
        self.nome = "Non impostato"
        self.identita = "Non impostata"
        self.origine = "Non impostata"
        self.tema = "Non impostato"
        self.descrizione = "Non impostato"
        self.classe = "Non impostato"
        self.abilita = ""   # EROICHE
        self.link = ""
        self.immagine = None
        self.hex_color = "#5865F2"


# =========================
# EMBED
# =========================

def create_embed(data: CharacterData):
    embed = discord.Embed(
        title=data.nome,
        description=data.descrizione,
        color=discord.Color.from_str(data.hex_color)
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


# =========================
# LOAD SINGLE
# =========================

def load_character(user_id, character_id=None):
    data = read_all()
    user_chars = data.get(str(user_id), {})

    if not user_chars:
        return None

    if character_id:
        raw = user_chars.get(character_id)
        if not raw:
            return None
        return _to_obj(character_id, raw)

    first_id = next(iter(user_chars))
    return _to_obj(first_id, user_chars[first_id])


# =========================
# LOAD ALL
# =========================

def load_all_characters(user_id):
    data = read_all()
    user_chars = data.get(str(user_id), {})

    return [
        _to_obj(cid, raw)
        for cid, raw in user_chars.items()
    ]


# =========================
# SAVE
# =========================

def save_character(user_id, data_obj):
    all_data = read_all()
    uid = str(user_id)

    if uid not in all_data:
        all_data[uid] = {}

    all_data[uid][data_obj.character_id] = {
        "character_id": data_obj.character_id,
        "nome": data_obj.nome,
        "identita": data_obj.identita,
        "origine": data_obj.origine,
        "tema": data_obj.tema,
        "descrizione": data_obj.descrizione,
        "classe": data_obj.classe,
        "abilita": data_obj.abilita,
        "link": data_obj.link,
        "immagine": data_obj.immagine,
        "hex_color": data_obj.hex_color
    }

    write_all(all_data)


# =========================
# DELETE (FIXED)
# =========================

def delete_character(user_id, character_id=None):
    """
    FIX IMPORTANTE:
    - ora ritorna False se NON elimina davvero nulla
    - evita falsi positivi (bug precedente)
    """

    all_data = read_all()
    uid = str(user_id)

    if uid not in all_data:
        return False

    if not all_data[uid]:
        return False

    user_chars = all_data[uid]

    if character_id:
        if character_id not in user_chars:
            return False
        del user_chars[character_id]
    else:
        first = next(iter(user_chars))
        del user_chars[first]

    # pulizia utente se vuoto
    if not user_chars:
        del all_data[uid]

    write_all(all_data)
    return True


# =========================
# INTERNAL
# =========================

def _to_obj(cid, data_dict):
    obj = CharacterData(character_id=cid)

    for k, v in data_dict.items():
        if k != "character_id":
            setattr(obj, k, v)

    return obj