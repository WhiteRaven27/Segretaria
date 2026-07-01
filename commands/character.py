import discord
from discord.ext import commands
import json
import os
import asyncio
import re

from .character_data import (
    CharacterData,
    create_embed,
    load_character,
    load_all_characters,
    save_character,
    delete_character,
    validate_character_id
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
# Hex modifica
# =========================

HEX_REGEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def normalize_hex(value: str | None):
    if not value:
        return None

    value = value.strip()

    if not HEX_REGEX.match(value):
        return None

    if len(value) == 4:
        value = "#" + "".join([c * 2 for c in value[1:]])

    return value.upper()

# =========================
# CHARACTER AUTOCOMPLETE
# =========================

async def character_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[discord.app_commands.Choice[str]]:
    """Autocomplete for character names"""
    chars = load_all_characters(interaction.user.id)
    
    # Filter characters by what the user typed
    matches = [c for c in chars if c.nome.lower().startswith(current.lower())]
    
    # Return as Discord choices (max 25)
    return [
        discord.app_commands.Choice(name=c.nome, value=c.character_id)
        for c in matches[:25]
    ]

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
            value = normalize_hex(value)

            if value is None:
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

        # Use async save_character with race condition protection
        try:
            await save_character(interaction.user.id, self.data)
        except ValueError as e:
            return await interaction.response.send_message(
                f"Errore: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            print(f"❌ Errore nel salvataggio: {e}")
            return await interaction.response.send_message(
                "Errore nel salvataggio della scheda.",
                ephemeral=True
            )

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
    async def nome(self, i, b):
        await self.open(i, "Nome", "nome")

    @discord.ui.button(label="Identità", style=discord.ButtonStyle.primary)
    async def identita(self, i, b):
        await self.open(i, "Identità", "identita")

    @discord.ui.button(label="Origine", style=discord.ButtonStyle.primary)
    async def origine(self, i, b):
        await self.open(i, "Origine", "origine")

    @discord.ui.button(label="Tema", style=discord.ButtonStyle.secondary)
    async def tema(self, i, b):
        await self.open(i, "Tema", "tema")

    @discord.ui.button(label="Descrizione", style=discord.ButtonStyle.secondary)
    async def descrizione(self, i, b):
        await self.open(i, "Descrizione", "descrizione")

    @discord.ui.button(label="Classe", style=discord.ButtonStyle.success)
    async def classe(self, i, b):
        await self.open(i, "Classe", "classe")

    @discord.ui.button(label="Eroiche", style=discord.ButtonStyle.success)
    async def abilita(self, i, b):
        await self.open(i, "Eroiche", "abilita")

    @discord.ui.button(label="Colore", style=discord.ButtonStyle.danger)
    async def colore(self, i, b):
        await self.open(i, "Colore", "hex_color")

    @discord.ui.button(label="Link", style=discord.ButtonStyle.secondary)
    async def link(self, i, b):
        await self.open(i, "Link", "link")

    @discord.ui.button(label="Immagine", style=discord.ButtonStyle.danger)
    async def immagine(self, i, b):
        await self.open(i, "Immagine", "immagine")

    @discord.ui.button(label="Salva", style=discord.ButtonStyle.success)
    async def salva(self, i, b):
        # Use async save_character with race condition protection
        try:
            await save_character(self.user_id, self.data)
            await i.response.send_message("Scheda salvata.", ephemeral=True)
        except ValueError as e:
            await i.response.send_message(f"Errore: {str(e)}", ephemeral=True)
            return
        except Exception as e:
            print(f"❌ Errore nel salvataggio: {e}")
            await i.response.send_message(
                "Errore nel salvataggio della scheda.",
                ephemeral=True
            )
            return

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

        # Validate character ID before deletion
        if not validate_character_id(self.cid):
            await i.response.edit_message(
                content="ID personaggio non valido.",
                view=None
            )
            return

        delete_character(i.user.id, self.cid)
        await i.response.edit_message(content="Personaggio eliminato.", view=None)

    @discord.ui.button(label="NO", style=discord.ButtonStyle.secondary)
    async def no(self, i, b):
        await i.response.edit_message(content="Operazione annullata.", view=None)


# =========================
# SHOW CONFIRM
# =========================

class ShowConfirm(discord.ui.View):
    def __init__(self, user, embed, bot):
        super().__init__(timeout=60)
        self.user = user
        self.embed = embed
        self.bot = bot

    @discord.ui.button(label="SI", style=discord.ButtonStyle.success)
    async def si(self, i, b):
        if i.user != self.user:
            return

        msg = await i.channel.send(
            content=f"Scheda di {self.user.mention}",
            embed=self.embed
        )
        
        # Track message owner in memory (only this bot session)
        self.bot.message_owners[msg.id] = self.user.id

        await i.response.edit_message(content="Pubblicato.", view=None)

    @discord.ui.button(label="NO", style=discord.ButtonStyle.danger)
    async def no(self, i, b):
        await i.response.edit_message(content="Annullato.", view=None)


# =========================
# COG
# =========================

class CharacterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(
        name="set-gallery",
        description="Imposta il canale dove verranno pubblicate le schede personaggio."
    )
    async def set_gallery(self, i, channel: discord.TextChannel):
        set_gallery_channel(i.guild.id, channel.id)
        await i.response.send_message("Canale impostato.", ephemeral=True)

    @discord.app_commands.command(
        name="crea",
        description="Crea una nuova scheda personaggio."
    )
    async def crea(self, i):
        d = CharacterData()
        v = EmbedEditor(d, user_id=i.user.id, bot=self.bot)

        await i.response.send_message(embed=create_embed(d), view=v, ephemeral=True)
        v.message = await i.original_response()

    @discord.app_commands.command(
        name="mostra",
        description="Mostra una tua scheda e la pubblica nel canale corrente."
    )
    @discord.app_commands.describe(
        personaggio="Nome del personaggio da mostrare"
    )
    @discord.app_commands.autocomplete(personaggio=character_autocomplete)
    async def mostra(self, i: discord.Interaction, personaggio: str):
        """Show a character by name with autocomplete"""
        d = load_character(i.user.id, personaggio)
        
        if not d:
            return await i.response.send_message(
                "Personaggio non trovato.",
                ephemeral=True
            )
        
        await i.response.send_message(
            "Vuoi mostrare questa scheda?",
            embed=create_embed(d),
            view=ShowConfirm(i.user, create_embed(d), self.bot),
            ephemeral=True
        )

    @discord.app_commands.command(
        name="modifica",
        description="Modifica una scheda personaggio esistente."
    )
    @discord.app_commands.describe(
        personaggio="Nome del personaggio da modificare"
    )
    @discord.app_commands.autocomplete(personaggio=character_autocomplete)
    async def modifica(self, i: discord.Interaction, personaggio: str):
        """Modify a character by name"""
        d = load_character(i.user.id, personaggio)
        
        if not d:
            return await i.response.send_message(
                "Personaggio non trovato.",
                ephemeral=True
            )
        
        await i.response.send_message(
            embed=create_embed(d),
            view=EmbedEditor(d, user_id=i.user.id, bot=self.bot),
            ephemeral=True
        )

    @discord.app_commands.command(
        name="elimina",
        description="Elimina un personaggio."
    )
    @discord.app_commands.describe(
        personaggio="Nome del personaggio da eliminare"
    )
    @discord.app_commands.autocomplete(personaggio=character_autocomplete)
    async def elimina(self, i: discord.Interaction, personaggio: str):
        """Delete a character by name"""
        d = load_character(i.user.id, personaggio)
        
        if not d:
            return await i.response.send_message(
                "Personaggio non trovato.",
                ephemeral=True
            )
        
        await i.response.send_message(
            embed=discord.Embed(
                title="Conferma eliminazione",
                description=d.nome,
                color=discord.Color.red()
            ),
            view=ConfirmDelete(i.user, personaggio),
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(CharacterCog(bot))
