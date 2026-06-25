import json
import discord
import uuid

class CharacterData:
    def __init__(self, character_id=None):
        self.character_id = character_id or str(uuid.uuid4())[:8]
        self.nome = "Non impostato"
        self.identita = "Non impostata"
        self.origine = "Non impostata"
        self.tema = "Non impostato"
        self.descrizione = "Non impostata"
        self.classe = "Non impostata"
        self.abilita = ""
        self.link = ""
        self.immagine = None
        self.hex_color = "#5865F2"


def create_embed(data: CharacterData):
    embed = discord.Embed(
        title=data.nome,
        description=data.descrizione,
        color=discord.Color.from_str(data.hex_color)
    )

    embed.add_field(name="Identita", value=data.identita, inline=True)
    embed.add_field(name="Origine", value=data.origine, inline=True)
    embed.add_field(name="Tema", value=data.tema, inline=True)
    embed.add_field(name="Classe", value=data.classe, inline=True)

    # Abilità opzionale
    if data.abilita:
        embed.add_field(name="Abilita Eroiche", value=data.abilita, inline=False)

    # LINK FIX INDENTAZIONE
    if data.link:
        embed.add_field(name="Link Scheda", value=data.link, inline=False)

    # Immagine opzionale
    if data.immagine:
        embed.set_image(url=data.immagine)

    embed.set_footer(text=f"Messaggio offerto da Vanguard Express")

    return embed


def load_character(user_id, character_id=None):
    try:
        with open("data/characters.json", "r") as f:
            characters = json.load(f)

        user_characters = characters.get(str(user_id), {})

        if not user_characters:
            return None

        if character_id:
            if character_id in user_characters:
                data_dict = user_characters[character_id]
                data = CharacterData(character_id=character_id)
                for key, value in data_dict.items():
                    if key != "character_id":
                        setattr(data, key, value)
                return data
        else:
            first_char_id = next(iter(user_characters))
            data_dict = user_characters[first_char_id]
            data = CharacterData(character_id=first_char_id)
            for key, value in data_dict.items():
                if key != "character_id":
                    setattr(data, key, value)
            return data

    except Exception as e:
        print("load_character error:", e)

    return None


def load_all_characters(user_id):
    try:
        with open("data/characters.json", "r") as f:
            characters = json.load(f)

        user_characters = characters.get(str(user_id), {})
        result = []

        for char_id, data_dict in user_characters.items():
            data = CharacterData(character_id=char_id)
            for key, value in data_dict.items():
                if key != "character_id":
                    setattr(data, key, value)
            result.append(data)

        return result

    except FileNotFoundError:
        return []
    except json.JSONDecodeError as e:
        print("load_all_characters JSON decode error:", e)
        raise
    except Exception as e:
        print("load_all_characters error:", e)
        raise


def save_character(user_id, data):
    try:
        with open("data/characters.json", "r") as f:
            characters = json.load(f)
    except FileNotFoundError:
        characters = {}

    user_id_str = str(user_id)

    if user_id_str not in characters:
        characters[user_id_str] = {}

    characters[user_id_str][data.character_id] = {
        "character_id": data.character_id,
        "nome": data.nome,
        "identita": data.identita,
        "origine": data.origine,
        "tema": data.tema,
        "descrizione": data.descrizione,
        "classe": data.classe,
        "abilita": data.abilita,
        "link": data.link,
        "immagine": data.immagine,
        "hex_color": data.hex_color
    }

    with open("data/characters.json", "w") as f:
        json.dump(characters, f, indent=4)


def delete_character(user_id, character_id=None):
    try:
        with open("data/characters.json", "r") as f:
            characters = json.load(f)

        user_id_str = str(user_id)

        if user_id_str not in characters:
            return False

        user_characters = characters[user_id_str]

        if not user_characters:
            return False

        if character_id:
            if character_id in user_characters:
                del user_characters[character_id]
            else:
                return False
        else:
            first_char_id = next(iter(user_characters))
            del user_characters[first_char_id]

        with open("data/characters.json", "w") as f:
            json.dump(characters, f, indent=4)

        return True

    except Exception as e:
        print("delete_character error:", e)

    return False
