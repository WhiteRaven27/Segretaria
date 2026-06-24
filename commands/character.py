import discord
from discord.ext import commands
import json
import os
import asyncio
from .character_data import (
    CharacterData,
    create_embed,
    load_character,
    load_all_characters,
    save_character,
    delete_character
)

# =========================
# GALLERY CONFIG
# =========================

GALLERY_CONFIG_FILE = "data/gallery_config.json"


def load_gallery_config():
    if os.path.exists(GALLERY_CONFIG_FILE):
        try:
            with open(GALLERY_CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_gallery_config(config):
    os.makedirs("data", exist_ok=True)
    with open(GALLERY_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


def get_gallery_channel(guild_id):
    config = load_gallery_config()
    return config.get(str(guild_id))


def set_gallery_channel(guild_id, channel_id):
    config = load_gallery_config()
    config[str(guild_id)] = channel_id
    save_gallery_config(config)


# =========================
# MODAL
# =========================

class EditModal(discord.ui.Modal):
    OPTIONAL_FIELDS = {"abilita", "link", "immagine"}

    def __init__(self, title, field_name, data, message, view):
        super().__init__(title=title)

        self.field_name = field_name
        self.data = data
        self.message = message
        self.view_ref = view

        required = field_name not in self.OPTIONAL_FIELDS

        self.input = discord.ui.TextInput(
            label=title,
            style=discord.TextStyle.paragraph,
            required=required,
            max_length=2000
        )

        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        value = self.input.value.strip()

        # =========================
        # HEX VALIDATION
        # =========================
        if self.field_name == "hex_color":
            if value and not (value.startswith("#") and len(value) in (4, 7)):
                await interaction.response.send_message(
                    "Colore non valido! Usa #FFF o #FFFFFF",
                    ephemeral=True
                )
                return
            if not value:
                value = None

        # =========================
        # OPTIONAL NORMALIZATION
        # =========================
        if self.field_name in self.OPTIONAL_FIELDS and not value:
            value = None

        # =========================
        # REQUIRED VALIDATION
        # =========================
        if self.field_name not in self.OPTIONAL_FIELDS:
            if not value:
                await interaction.response.send_message(
                    "Questo campo non può essere vuoto.",
                    ephemeral=True
                )
                return

        # =========================
        # APPLY SAFE VALUE
        # =========================
        setattr(self.data, self.field_name, value)
        save_character(interaction.user.id, self.data)

        await self.message.edit(
            embed=create_embed(self.data),
            view=self.view_ref
        )

        await interaction.response.defer()


# =========================
# VIEW (EDITOR)
# =========================

class EmbedEditor(discord.ui.View):
    def __init__(self, data, message=None, user_id=None, bot=None):
        super().__init__(timeout=None)
        self.data = data
        self.message = message
        self.user_id = user_id
        self.bot = bot

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
    async def nome_button(self, interaction, button):
        await self.open_modal(interaction, "Nome", "nome")

    @discord.ui.button(label="Identità", style=discord.ButtonStyle.primary)
    async def identita_button(self, interaction, button):
        await self.open_modal(interaction, "Identità", "identita")

    @discord.ui.button(label="Origine", style=discord.ButtonStyle.primary)
    async def origine_button(self, interaction, button):
        await self.open_modal(interaction, "Origine", "origine")

    @discord.ui.button(label="Tema", style=discord.ButtonStyle.secondary)
    async def tema_button(self, interaction, button):
        await self.open_modal(interaction, "Tema", "tema")

    @discord.ui.button(label="Descrizione", style=discord.ButtonStyle.secondary)
    async def descrizione_button(self, interaction, button):
        await self.open_modal(interaction, "Descrizione", "descrizione")

    @discord.ui.button(label="Classe", style=discord.ButtonStyle.success)
    async def classe_button(self, interaction, button):
        await self.open_modal(interaction, "Classe", "classe")

    @discord.ui.button(label="Abilità", style=discord.ButtonStyle.success)
    async def abilita_button(self, interaction, button):
        await self.open_modal(interaction, "Abilità", "abilita")

    @discord.ui.button(label="Colore", style=discord.ButtonStyle.danger)
    async def hex_button(self, interaction, button):
        await self.open_modal(interaction, "Colore", "hex_color")

    @discord.ui.button(label="Immagine", style=discord.ButtonStyle.danger)
    async def immagine_button(self, interaction, button):
        await self.open_modal(interaction, "Immagine", "immagine")

    # =========================
    # SALVA FIXED
    # =========================
    @discord.ui.button(label="Salva", style=discord.ButtonStyle.success)
    async def salva_button(self, interaction, button):

        save_character(self.user_id, self.data)

        await interaction.response.send_message(
            "Personaggio salvato!",
            ephemeral=True
        )

        async def post_gallery():
            if not interaction.guild:
                return

            channel_id = get_gallery_channel(interaction.guild.id)
            if not channel_id or not self.bot:
                return

            try:
                channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)

                if channel:
                    embed = create_embed(self.data)
                    await channel.send(
                        content=f"Aggiornato da {interaction.user.mention}",
                        embed=embed
                    )
            except Exception as e:
                print("Errore gallery:", e)

        asyncio.create_task(post_gallery())


# =========================
# COMMANDS
# =========================

class CharacterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ✔ ADMIN COMMAND RESTORED
    @discord.app_commands.command(name="set-gallery", description="Imposta il canale galleria")
    @discord.app_commands.checks.has_permissions(administrator=True)
    async def set_gallery(self, interaction: discord.Interaction, channel: discord.TextChannel):

        set_gallery_channel(interaction.guild.id, channel.id)

        await interaction.response.send_message(
            f"Galleria impostata su {channel.mention}",
            ephemeral=True
        )

    @discord.app_commands.command(name="crea")
    async def crea(self, interaction: discord.Interaction):

        data = CharacterData()
        view = EmbedEditor(data, user_id=interaction.user.id, bot=self.bot)

        await interaction.response.send_message(
            embed=create_embed(data),
            view=view,
            ephemeral=True
        )

        msg = await interaction.original_response()
        view.message = msg


async def setup(bot):
    await bot.add_cog(CharacterCog(bot))
