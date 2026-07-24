import discord
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
        name="modifica",
        description="Modifica l'hex color di una scheda personaggio."
    )
    @discord.app_commands.describe(
        personaggio="Nome del personaggio",
        hex="Colore hex (es. #FF5733 o #FFF, opzionale)"
    )
    @discord.app_commands.autocomplete(personaggio=character_autocomplete)
    async def modifica(self, i: discord.Interaction, personaggio: str, hex: str = None):
        d = await load_character(i.user.id, personaggio)
        if not d:
            return await i.response.send_message("Personaggio non trovato.", ephemeral=True)

        if hex is not None:
            hex_color = normalize_hex(hex)
            if hex_color is None:
                return await i.response.send_message(
                    "Colore non valido. Usa #FFF o #FFFFFF.", ephemeral=True
                )
            d.hex_color = hex_color
            try:
                await save_character(i.user.id, d)
                embed = create_embed(d)
                await i.response.send_message(
                    f"Colore aggiornato a {hex_color}!", embed=embed, ephemeral=True
                )
            except Exception as e:
                await i.response.send_message(f"Errore: {str(e)}", ephemeral=True)
        else:
            embed = create_embed(d)
            await i.response.send_message(
                embed=embed,
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(CharacterCog(bot))
