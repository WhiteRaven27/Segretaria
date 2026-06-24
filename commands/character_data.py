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
        self.abilita = ""  # Ora opzionale
        self.link = ""  # opzionale
        self.immagine = None
        self.hex_color = "#5865F2"

def create_embed(data: CharacterData):
    """Crea un embed dal CharacterData"""
    embed = discord.Embed(
        title=data.nome,
        description=data.descrizione,
        color=discord.Color.from_str(data.hex_color)
    )

    embed.add_field(name="Identita", value=data.identita, inline=True)
    embed.add_field(name="Origine", value=data.origine, inline=True)
    embed.add_field(name="Tema", value=data.tema, inline=True)
    embed.add_field(name="Classe", value=data.classe, inline=True)
    
    # Mostra Abilità solo se non vuota
    if data.abilita:
        embed.add_field(name="Abilita Eroiche", value=data.abilita, inline=False)
        
    if data.link:
        embed.add_field(name="Link Scheda", value=data.link, inline=False)

    if data.immagine:
        embed.set_image(url=data.immagine)

    embed.set_footer(text="Editor personaggio interattivo")

    return embed

def load_character(user_id, character_id=None):
    """Carica il personaggio dell'utente dal file JSON.
    Se character_id non è specificato, carica il primo personaggio."""
    try:
        with open("data/characters.json", "r") as f:
            characters = json.load(f)
        
        user_characters = characters.get(str(user_id), {})
        
        if not user_characters:
            return None
        
        # Se character_id è specificato, carica quel personaggio
        if character_id:
            if character_id in user_characters:
                data_dict = user_characters[character_id]
                data = CharacterData(character_id=character_id)
                for key, value in data_dict.items():
                    if key != "character_id":
                        setattr(data, key, value)
                return data
        else:
            # Altrimenti carica il primo personaggio
            first_char_id = next(iter(user_characters))
            data_dict = user_characters[first_char_id]
            data = CharacterData(character_id=first_char_id)
            for key, value in data_dict.items():
                if key != "character_id":
                    setattr(data, key, value)
            return data
    except:
        pass
    
    return None

def load_all_characters(user_id):
    """Carica tutti i personaggi dell'utente"""
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
    except:
        pass
    
    return []

def _character(user_id, data):
    """Salva il personaggio dell'utente nel file JSON"""
    try:
        with open("data/characters.json", "r") as f:
            characters = json.load(f)
    except:
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
    """Elimina il personaggio dell'utente.
    Se character_id non è specificato, elimina il primo personaggio."""
    try:
        with open("data/characters.json", "r") as f:
            characters = json.load(f)
        
        user_id_str = str(user_id)
        if user_id_str not in characters:
            return False
        
        user_characters = characters[user_id_str]
        
        if not user_characters:
            return False
        
        # Se character_id è specificato, elimina quel personaggio
        if character_id:
            if character_id in user_characters:
                del user_characters[character_id]
        else:
            # Altrimenti elimina il primo personaggio
            first_char_id = next(iter(user_characters))
            del user_characters[first_char_id]
        
        with open("data/characters.json", "w") as f:
            json.dump(characters, f, indent=4)
        return True
    except:
        pass
    
    return False

