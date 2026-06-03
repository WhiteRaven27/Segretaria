import json
import discord

class CharacterData:
    def __init__(self):
        self.nome = "Non impostato"
        self.identita = "Non impostata"
        self.origine = "Non impostata"
        self.tema = "Non impostato"
        self.descrizione = "Non impostata"
        self.classe = "Non impostata"
        self.abilita = "Non impostate"
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
    embed.add_field(name="Abilita Eroiche", value=data.abilita, inline=False)

    if data.immagine:
        embed.set_image(url=data.immagine)

    embed.set_footer(text="Editor personaggio interattivo")

    return embed

def load_character(user_id):
    """Carica il personaggio dell'utente dal file JSON"""
    try:
        with open("data/characters.json", "r") as f:
            characters = json.load(f)
        
        if str(user_id) in characters:
            data_dict = characters[str(user_id)]
            data = CharacterData()
            for key, value in data_dict.items():
                setattr(data, key, value)
            return data
    except:
        pass
    
    return None

def save_character(user_id, data):
    """Salva il personaggio dell'utente nel file JSON"""
    try:
        with open("data/characters.json", "r") as f:
            characters = json.load(f)
    except:
        characters = {}
    
    characters[str(user_id)] = {
        "nome": data.nome,
        "identita": data.identita,
        "origine": data.origine,
        "tema": data.tema,
        "descrizione": data.descrizione,
        "classe": data.classe,
        "abilita": data.abilita,
        "immagine": data.immagine,
        "hex_color": data.hex_color
    }
    
    with open("data/characters.json", "w") as f:
        json.dump(characters, f, indent=4)

def delete_character(user_id):
    """Elimina il personaggio dell'utente"""
    try:
        with open("data/characters.json", "r") as f:
            characters = json.load(f)
        
        if str(user_id) in characters:
            del characters[str(user_id)]
            
            with open("data/characters.json", "w") as f:
                json.dump(characters, f, indent=4)
            return True
    except:
        pass
    
    return False
