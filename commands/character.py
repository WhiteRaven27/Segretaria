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
    return load_gallery_config().get(str(guild_id))


def set_gallery_channel(guild_id, channel_id):
    config = load_gallery_config()
    config[str(guild_id)] = channel_id
    save_gallery_config(config)


# =========================
# EDIT MODAL
# =========================

class EditModal(discord.ui.Modal):
    OPTIONAL = {"abilita", "link", "immagine"}

    def __init__(self, title, field, data, message, view):
        super().__init__(title=title)

        self.field = field
        self.data = data
        self.message = message
        self.view = view

        self.input = discord.ui.TextInput(
            label=title,
            style=discord.TextStyle.paragraph,
            required=field not in self.OPTIONAL
        )

        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        value = self.input.value.strip()

        if self.field == "hex_color":
            if value and not (value.startswith("#") and len(value) in (4, 7)):
                return await interaction.response.send_message(
                    "Colore non valido (#FFF o #FFFFFF)",
                    ephemeral=True
                )
            if not value:
                value = None

        if self.field in self.OPTIONAL and not value:
            value = None

        if self.field not in self.OPTIONAL and not value:
            return await interaction.response.send_message(
                "Campo obbligatorio",
                ephemeral=True
            )

        setattr(self.data, self.field, value)

        save_character(interaction.user.id, self.data)

        await self.message.edit(embed=create_embed(self.data), view=self.view)
        await interaction.response.defer()


# =========================
# EDITOR VIEW
# =========================

class EmbedEditor(discord.ui.View):
    def __init__(self, data, message=None, user_id=None, bot=None):
        super().__init__(timeout=None)
        self.data = data
        self.message = message
        self.user_id = user_id
        self.bot = bot

    async def open(self, interaction, title, field):
        await interaction.response.send_modal(
            EditModal(title, field, self.data, self.message, self)
        )

    @discord.ui.button(label="Nome", style=discord.ButtonStyle.primary)
    async def nome(self, i, b): await self.open(i, "Nome", "nome")

    @discord.ui.button(label="Identità", style=discord.ButtonStyle.primary)
    async def identita(self, i, b): await self.open(i, "Identità", "identita")

    @discord.ui.button(label="Origine", style=discord.ButtonStyle.primary)
    async def origine(self, i, b): await self.open(i, "Origine", "origine")

    @discord.ui.button(label="Tema", style=discord.ButtonStyle.secondary)
    async def tema(self, i, b): await self.open(i, "Tema", "tema")

    @discord.ui.button(label="Descrizione", style=discord.ButtonStyle.secondary)
    async def descrizione(self, i, b): await self.open(i, "Descrizione", "descrizione")

    @discord.ui.button(label="Classe", style=discord.ButtonStyle.success)
    async def classe(self, i, b): await self.open(i, "Classe", "classe")

    @discord.ui.button(label="Abilità", style=discord.ButtonStyle.success)
    async def abilita(self, i, b): await self.open(i, "Abilità", "abilita")

    @discord.ui.button(label="Colore", style=discord.ButtonStyle.danger)
    async def colore(self, i, b): await self.open(i, "Colore", "hex_color")

    @discord.ui.button(label="Link", style=discord.ButtonStyle.secondary)
    async def link(self, i, b): await self.open(i, "Link", "link")

    @discord.ui.button(label="Immagine", style=discord.ButtonStyle.danger)
    async def immagine(self, i, b): await self.open(i, "Immagine", "immagine")

    @discord.ui.button(
        label="Salva",
        style=discord.ButtonStyle.success
    )
    async def salva(self, i, b):

        save_character(self.user_id, self.data)

        await i.response.send_message("Salvato", ephemeral=True)

        async def post():
            if not i.guild:
                return

            cid = get_gallery_channel(i.guild.id)
            if not cid:
                return

            ch = self.bot.get_channel(cid)
            if ch:
                await ch.send(embed=create_embed(self.data))

        asyncio.create_task(post())


# =========================
# SELECT
# =========================

class SelectCharacter(discord.ui.View):
    def __init__(self, user, chars, callback):
        super().__init__(timeout=60)
        self.user = user
        self.callback = callback

        self.select = discord.ui.Select(
            placeholder="Seleziona personaggio",
            options=[
                discord.SelectOption(label=c.nome[:100], value=c.character_id)
                for c in chars
            ]
        )

        self.select.callback = self.on
        self.add_item(self.select)

    async def on(self, i):
        if i.user != self.user:
            return await i.response.send_message("No", ephemeral=True)
        await self.callback(i, self.select.values[0])


# =========================
# CONFIRM DELETE
# =========================

class ConfirmDelete(discord.ui.View):
    def __init__(self, user, cid):
        super().__init__(timeout=30)
        self.user = user
        self.cid = cid

    @discord.ui.button(label="SI", style=discord.ButtonStyle.danger)
    async def si(self, i, b):
        if i.user != self.user:
            return
        delete_character(i.user.id, self.cid)
        await i.response.edit_message(content="Eliminato", view=None)

    @discord.ui.button(label="NO", style=discord.ButtonStyle.secondary)
    async def no(self, i, b):
        await i.response.edit_message(content="Annullato", view=None)


# =========================
# SHOW CONFIRM
# =========================

class ShowConfirm(discord.ui.View):
    def __init__(self, user, embed):
        super().__init__(timeout=60)
        self.user = user
        self.embed = embed

    @discord.ui.button(label="SI", style=discord.ButtonStyle.success)
    async def si(self, i, b):
        if i.user != self.user:
            return

        await i.channel.send(
            content=f"Scheda di {self.user.mention}",
            embed=self.embed
        )

        await i.response.edit_message(content="Pubblicato", view=None)

    @discord.ui.button(label="NO", style=discord.ButtonStyle.danger)
    async def no(self, i, b):
        await i.response.edit_message(content="Annullato", view=None)


# =========================
# COG
# =========================

class CharacterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(
        name="set-gallery",
        description="Imposta il canale per pubblicare le schede"
    )
    async def set_gallery(self, i, channel: discord.TextChannel):
        set_gallery_channel(i.guild.id, channel.id)
        await i.response.send_message("OK", ephemeral=True)

    @discord.app_commands.command(
        name="crea",
        description="Crea una nuova scheda personaggio"
    )
    async def crea(self, i):
        d = CharacterData()
        v = EmbedEditor(d, user_id=i.user.id, bot=self.bot)

        await i.response.send_message(embed=create_embed(d), view=v, ephemeral=True)
        v.message = await i.original_response()

    @discord.app_commands.command(
        name="mostra",
        description="Mostra una tua scheda e la pubblica"
    )
    async def mostra(self, i):
        chars = load_all_characters(i.user.id)

        if not chars:
            return await i.response.send_message("Nessun personaggio", ephemeral=True)

        async def h(inter, cid):
            d = load_character(i.user.id, cid)
            await inter.response.send_message(
                "Vuoi mostrare questa scheda?",
                embed=create_embed(d),
                view=ShowConfirm(i.user, create_embed(d)),
                ephemeral=True
            )

        if len(chars) == 1:
            await h(i, chars[0].character_id)
        else:
            await i.response.send_message(
                "Seleziona personaggio",
                view=SelectCharacter(i.user, chars, h),
                ephemeral=True
            )

    @discord.app_commands.command(
        name="modifica",
        description="Modifica una scheda esistente"
    )
    async def modifica(self, i):
        chars = load_all_characters(i.user.id)

        if not chars:
            return await i.response.send_message("Nessun personaggio", ephemeral=True)

        async def h(inter, cid):
            d = load_character(i.user.id, cid)
            await inter.response.send_message(
                embed=create_embed(d),
                view=EmbedEditor(d, user_id=i.user.id, bot=self.bot),
                ephemeral=True
            )

        if len(chars) == 1:
            await h(i, chars[0].character_id)
        else:
            await i.response.send_message(
                "Seleziona personaggio",
                view=SelectCharacter(i.user, chars, h),
                ephemeral=True
            )

    @discord.app_commands.command(
        name="elimina",
        description="Elimina una scheda personaggio"
    )
    async def elimina(self, i):
        chars = load_all_characters(i.user.id)

        if not chars:
            return await i.response.send_message("Nessun personaggio", ephemeral=True)

        async def h(inter, cid):
            d = load_character(i.user.id, cid)
            await i.response.send_message(
                embed=discord.Embed(
                    title="Eliminare?",
                    description=d.nome,
                    color=discord.Color.red()
                ),
                view=ConfirmDelete(i.user, cid),
                ephemeral=True
            )

        if len(chars) == 1:
            await h(i, chars[0].character_id)
        else:
            await i.response.send_message(
                "Seleziona personaggio",
                view=SelectCharacter(i.user, chars, h),
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(CharacterCog(bot))
