import sys

path = r'c:\Users\dalid\Desktop\Segretaria-main\Segretaria-main\commands\character.py'

code = r"""import discord
from discord.ext import commands
import asyncio

from .message_owners_store import save_message_owners
from .character_data import (
    CharacterData,
    create_embed,
    load_character,
    load_all_characters,
    save_character,
    delete_character,
    validate_character_id
)
from .gallery_store import get_gallery_channel, set_gallery_channel
from .sheet import normalize_hex

async def character_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[discord.app_commands.Choice[str]]:
    chars = await load_all_characters(interaction.user.id)
    matches = [c for c in chars if c.nome.lower().startswith(current.lower())]
    return [
        discord.app_commands.Choice(name=c.nome, value=c.character_id)
        for c in matches[:25]
    ]

class HexModal(discord.ui.Modal):
    def __init__(self, data, user_id, bot):
        super().__init__(title="Colore Embed")
        self.data = data
        self.user_id = user_id
        self.bot = bot
        current = data.hex_color or "#5865F2"
        self.input = discord.ui.TextInput(
            label="Hex Colore (#RRGGBB o #RGB)",
            style=discord.TextStyle.short,
            required=True,
            default=current,
            placeholder="es. #FF5733"
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Non puoi modificare questa scheda.", ephemeral=True)
        value = self.input.value.strip()
        hex_color = normalize_hex(value)
        if hex_color is None:
            return await interaction.response.send_message(
                "Colore non valido. Usa #FFF o #FFFFFF.", ephemeral=True
            )
        self.data.hex_color = hex_color
        try:
            await save_character(self.user_id, self.data)
            embed = create_embed(self.data)
            await interaction.response.send_message(
                "Colore hex aggiornato!", embed=embed, ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"Errore: {str(e)}", ephemeral=True)

class ShowConfirm(discord.ui.View):
    def __init__(self, user, embed, bot):
        super().__init__(timeout=60)
        self.user = user
        self.embed = embed
        self.bot = bot

    @discord.ui.button(label="SI", style=discord.ButtonStyle.success)
    async def si(self, i, b):
        if i.user != self.user:
            await i.response.defer()
            return
        msg = await i.channel.send(
            content=f"Scheda di {self.user.mention}",
            embed=self.embed
        )
        self.bot.message_owners[msg.id] = self.user.id
        await save_message_owners(self.bot.message_owners)
        await i.response.edit_message(content="Pubblicato.", view=None)

    @discord.ui.button(label="NO", style=discord.ButtonStyle.danger)
    async def no(self, i, b):
        await i.response.edit_message(content="Annullato.", view=None)

class CharacterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(
        name="set-gallery",
        description="Imposta il canale dove verranno pubblicate le schede personaggio."
    )
    async def set_gallery(self, i, channel: discord.TextChannel):
        await set_gallery_channel(i.guild.id, channel.id)
        await i.response.send_message("Canale impostato.", ephemeral=True)

    @discord.app_commands.command(
        name="mostra",
        description="Mostra una tua scheda e la pubblica nel canale corrente."
    )
    @discord.app_commands.describe(personaggio="Nome del personaggio da mostrare")
    @discord.app_commands.autocomplete(personaggio=character_autocomplete)
    async def mostra(self, i: discord.Interaction, personaggio: str):
        d = await load_character(i.user.id, personaggio)
        if not d:
            return await i.response.send_message("Personaggio non trovato.", ephemeral=True)
        await i.response.send_message(
            "Vuoi mostrare questa scheda?",
            embed=create_embed(d),
            view=ShowConfirm(i.user, create_embed(d), self.bot),
            ephemeral=True
        )

    @discord.app_commands.command(
        name="hex",
        description="Cambia il colore hex dell'embed di una scheda personaggio."
    )
    @discord.app_commands.describe(personaggio="Nome del personaggio")
    @discord.app_commands.autocomplete(personaggio=character_autocomplete)
    async def cmd_hex(self, i: discord.Interaction, personaggio: str):
        d = await load_character(i.user.id, personaggio)
        if not d:
            return await i.response.send_message("Personaggio non trovato.", ephemeral=True)
        modal = HexModal(d, user_id=i.user.id, bot=self.bot)
        await i.response.send_modal(modal)

async def setup(bot):
    await bot.add_cog(CharacterCog(bot))
"""

with open(path, 'w', encoding='utf-8') as f:
    f.write(code.lstrip())

print(f"Written {len(code)} chars to character.py")

# Verify it compiles
