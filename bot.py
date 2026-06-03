import os
from dotenv import load_dotenv
import json

# Load environment variables from .env file (if it exists)
load_dotenv()

TOKEN = os.getenv("TOKEN")

# Make sure data directory exists
if not os.path.exists("data"):
    os.makedirs("data")

if not os.path.exists("data/characters.json"):
    with open("data/characters.json", "w") as f:
        json.dump({}, f)

import discord
from discord.ext import commands


intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# DATI EMBED
# =========================

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

# =========================
# FUNZIONE EMBED
# =========================


def create_embed(data: CharacterData):
    embed = discord.Embed(
        title=data.nome,
        description=data.descrizione,
        color=discord.Color.from_str(data.hex_color)
    )

    embed.add_field(name="🪪 Identità", value=data.identita, inline=True)
    embed.add_field(name="🌍 Origine", value=data.origine, inline=True)
    embed.add_field(name="🎨 Tema", value=data.tema, inline=True)
    embed.add_field(name="⚔️ Classe", value=data.classe, inline=True)
    embed.add_field(name="✨ Abilità Eroiche", value=data.abilita, inline=False)

    if data.immagine:
        embed.set_image(url=data.immagine)

    embed.add_field(name="🎨 Hex Color", value=data.hex_color, inline=True)

    embed.set_footer(text="Editor personaggio interattivo")

    return embed

# =========================
# FUNZIONI PER PERSISTENZA
# =========================

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

# =========================
# MODAL GENERICO
# =========================

class EditModal(discord.ui.Modal):
    def __init__(self, title, field_name, data, message, view):
        super().__init__(title=title)

        self.field_name = field_name
        self.data = data
        self.message = message
        self.view_ref = view

        self.input = discord.ui.TextInput(
            label=title,
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        setattr(self.data, self.field_name, str(self.input))
        save_character(interaction.user.id, self.data)

        await self.message.edit(
            embed=create_embed(self.data),
            view=self.view_ref
        )

        await interaction.response.send_message(
            f"✅ Campo aggiornato: {self.field_name}",
            ephemeral=True
        )

# =========================
# VIEW CON PULSANTI
# =========================

class EmbedEditor(discord.ui.View):
    def __init__(self, data, message=None, user_id=None):
        super().__init__(timeout=None)
        self.data = data
        self.message = message
        self.user_id = user_id

    async def open_modal(self, interaction, title, field_name):
        modal = EditModal(
            title=title,
            field_name=field_name,
            data=self.data,
            message=self.message,
            view=self
        )

        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Nome", style=discord.ButtonStyle.primary)
    async def nome_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Nome", "nome")

    @discord.ui.button(label="Identità", style=discord.ButtonStyle.primary)
    async def identita_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Identità", "identita")

    @discord.ui.button(label="Origine", style=discord.ButtonStyle.primary)
    async def origine_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Origine", "origine")

    @discord.ui.button(label="Tema", style=discord.ButtonStyle.secondary)
    async def tema_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Tema", "tema")

    @discord.ui.button(label="Descrizione", style=discord.ButtonStyle.secondary)
    async def descrizione_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Descrizione", "descrizione")

    @discord.ui.button(label="Classe", style=discord.ButtonStyle.success)
    async def classe_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Classe", "classe")

    @discord.ui.button(label="Abilità", style=discord.ButtonStyle.success)
    async def abilita_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Abilità Eroiche", "abilita")

    @discord.ui.button(label="Hex Color", style=discord.ButtonStyle.danger)
    async def hex_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Hex Color (#FFFFFF)", "hex_color")

    @discord.ui.button(label="Immagine", style=discord.ButtonStyle.danger)
    async def immagine_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Link Immagine", "immagine")

    @discord.ui.button(label="Salva Personaggio", style=discord.ButtonStyle.success)
    async def salva_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        save_character(self.user_id, self.data)
        await interaction.response.send_message(
            f"✅ Personaggio salvato!",
            ephemeral=True
        )

# =========================
# COMANDO
# =========================

@bot.command()
async def crea(ctx):
    data = CharacterData()

    view = EmbedEditor(data, user_id=ctx.author.id)

    message = await ctx.send(
        embed=create_embed(data),
        view=view
    )

    view.message = message

# =========================
# SLASH COMMAND /mostra
# =========================

class ConfirmView(discord.ui.View):
    def __init__(self, user, embed):
        super().__init__(timeout=60)
        self.user = user
        self.embed = embed

    @discord.ui.button(label="Sì", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user != self.user:
            await interaction.response.send_message(
                "❌ Non puoi confermare questo personaggio.",
                ephemeral=True
            )
            return

        await interaction.channel.send(
            content=f"📢 Personaggio inviato da {self.user.mention}",
            embed=self.embed
        )

        await interaction.response.edit_message(
            content="✅ Personaggio inviato.",
            view=None,
            embed=None
        )

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user != self.user:
            await interaction.response.send_message(
                "❌ Non puoi annullare questo personaggio.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content="❌ Invio annullato.",
            view=None,
            embed=None
        )

@bot.tree.command(name="mostra", description="Mostra il personaggio salvato")
async def mostra(interaction: discord.Interaction):
    data = load_character(interaction.user.id)
    
    if data is None:
        await interaction.response.send_message(
            "❌ Non hai un personaggio salvato. Usa `/crea` per crearne uno!",
            ephemeral=True
        )
        return

    embed = create_embed(data)
    view = ConfirmView(interaction.user, embed)

    await interaction.response.send_message(
        content="Questo va bene?",
        embed=embed,
        view=view,
        ephemeral=True
    )

# =========================
# SLASH COMMAND /modifica
# =========================

@bot.tree.command(name="modifica", description="Modifica il tuo personaggio")
async def modifica(interaction: discord.Interaction):
    data = load_character(interaction.user.id)
    
    if data is None:
        await interaction.response.send_message(
            "❌ Non hai un personaggio salvato. Usa `/crea` per crearne uno!",
            ephemeral=True
        )
        return

    view = EmbedEditor(data, user_id=interaction.user.id)
    message = await interaction.response.send_message(
        embed=create_embed(data),
        view=view,
        ephemeral=True
    )

    view.message = await interaction.original_response()

# =========================
# SLASH COMMAND /elimina
# =========================

class ConfirmDeleteView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=60)
        self.user = user

    @discord.ui.button(label="Sì, elimina", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message(
                "❌ Non puoi eliminare il personaggio di un altro.",
                ephemeral=True
            )
            return

        if delete_character(self.user.id):
            await interaction.response.edit_message(
                content="🗑️ Personaggio eliminato permanentemente.",
                view=None
            )
        else:
            await interaction.response.send_message(
                "❌ Errore nell'eliminazione del personaggio.",
                ephemeral=True
            )

    @discord.ui.button(label="No, annulla", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message(
                "❌ Non puoi annullare l'eliminazione del personaggio di un altro.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content="❌ Eliminazione annullata.",
            view=None
        )

@bot.tree.command(name="elimina", description="Elimina il tuo personaggio")
async def elimina(interaction: discord.Interaction):
    data = load_character(interaction.user.id)
    
    if data is None:
        await interaction.response.send_message(
            "❌ Non hai un personaggio salvato.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="⚠️ Conferma Eliminazione",
        description=f"Sei sicuro di voler eliminare il personaggio **{data.nome}**? Questa azione è irreversibile!",
        color=discord.Color.red()
    )

    view = ConfirmDeleteView(interaction.user)
    await interaction.response.send_message(
        embed=embed,
        view=view,
        ephemeral=True
    )

# =========================
# AVVIO BOT
# =========================

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands sincronizzati: {len(synced)}")
    except Exception as e:
        print(e)

    print(f"Connesso come {bot.user}")

bot.run(TOKEN)
