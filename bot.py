import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")

import discord
from discord.ext import commands


intents = discord.Intents.default()
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
    def __init__(self, data, message=None):
        super().__init__(timeout=None)
        self.data = data
        self.message = message

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

# =========================
# COMANDO
# =========================

@bot.command()
async def crea(ctx):
    data = CharacterData()

    view = EmbedEditor(data)

    message = await ctx.send(
        embed=create_embed(data),
        view=view
    )

    view.message = message

# =========================
# SLASH COMMAND /personaggio mostra
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

# =========================
# COMANDO SLASH
# =========================

@bot.tree.command(name="mostra", description="Mostra il personaggio")
async def mostra(interaction: discord.Interaction):

    # Qui puoi recuperare i dati salvati del personaggio
    data = CharacterData()

    data.nome = "Eroe"
    data.identita = "Sconosciuta"
    data.origine = "Terra"
    data.tema = "Luce"
    data.descrizione = "Un potente guerriero"
    data.classe = "Tank"
    data.abilita = "Colpo eroico"

    embed = create_embed(data)

    view = ConfirmView(interaction.user, embed)

    await interaction.response.send_message(
        content="Questo va bene?",
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

import json
import os

if not os.path.exists("data"):
    os.makedirs("data")

if not os.path.exists("data/characters.json"):
    with open("data/characters.json", "w") as f:
        json.dump({}, f)