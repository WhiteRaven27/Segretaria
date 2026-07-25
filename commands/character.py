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


# ─────────────────────────────────────────
# MODAL per modificare descrizione
# ─────────────────────────────────────────

class DescrizioneModal(discord.ui.Modal):
    def __init__(self, data: CharacterData, message: discord.Message, view: discord.ui.View):
        super().__init__(title="Modifica Descrizione")
        self.data = data
        self.message = message
        self.view = view

        current = data.descrizione or ""
        if current == "Non impostata":
            current = ""

        self.input = discord.ui.TextInput(
            label="Descrizione",
            style=discord.TextStyle.paragraph,
            required=False,
            default=str(current) if current else None
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        value = self.input.value.strip() if self.input.value else ""
        self.data.descrizione = value if value else "Non impostata"

        embed = create_embed(self.data)
        await self.message.edit(embed=embed, view=self.view)
        await interaction.response.defer()


# ─────────────────────────────────────────
# MODAL per modificare hex
# ─────────────────────────────────────────

class HexModal(discord.ui.Modal):
    def __init__(self, data: CharacterData, message: discord.Message, view: discord.ui.View):
        super().__init__(title="Modifica Colore Hex")
        self.data = data
        self.message = message
        self.view = view

        self.input = discord.ui.TextInput(
            label="Colore (es. #FF5733 o #FFF)",
            style=discord.TextStyle.short,
            required=False,
            default=str(data.hex_color) if data.hex_color else "#5865F2"
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        value = self.input.value.strip() if self.input.value else ""
        if value:
            hex_color = normalize_hex(value)
            if hex_color is None:
                return await interaction.response.send_message(
                    "Colore non valido. Usa #FFF o #FFFFFF.", ephemeral=True
                )
            self.data.hex_color = hex_color
        else:
            self.data.hex_color = "#5865F2"

        embed = create_embed(self.data)
        await self.message.edit(embed=embed, view=self.view)
        await interaction.response.defer()


# ─────────────────────────────────────────
# VIEW per modifica (bottoni Descrizione, Hex, Salva)
# ─────────────────────────────────────────

class ModificaView(discord.ui.View):
    def __init__(self, data: CharacterData, user_id: int, bot):
        super().__init__(timeout=600)  # 10 minuti
        self.data = data
        self.user_id = user_id
        self.bot = bot
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.defer(ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

    @discord.ui.button(label="Descrizione", style=discord.ButtonStyle.primary)
    async def btn_descrizione(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_modal(DescrizioneModal(self.data, self.message, self))

    @discord.ui.button(label="Hex", style=discord.ButtonStyle.secondary)
    async def btn_hex(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_modal(HexModal(self.data, self.message, self))

    @discord.ui.button(label="Salva", style=discord.ButtonStyle.success)
    async def btn_salva(self, i: discord.Interaction, b: discord.ui.Button):
        try:
            await save_character(self.user_id, self.data)
        except Exception as e:
            await i.response.send_message(f"Errore nel salvataggio: {str(e)}", ephemeral=True)
            return

        # Pubblica in galleria automaticamente
        async def post_to_gallery():
            try:
                if not i.guild:
                    return
                cid = await get_gallery_channel(i.guild.id)
                if not cid:
                    return
                ch = self.bot.get_channel(cid)
                if ch:
                    msg = await ch.send(
                        content=f"Scheda di {i.user.mention}",
                        embed=create_embed(self.data)
                    )
                    # Traccia il messaggio per la cancellazione con ❌
                    self.bot.message_owners[msg.id] = i.user.id
                    await save_message_owners(self.bot.message_owners)
            except Exception as e:
                print(f"❌ Errore nel post gallery: {e}")

        asyncio.create_task(post_to_gallery())

        # Disabilita i bottoni dopo il salvataggio
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)
        await i.response.send_message("✅ Scheda salvata e pubblicata in galleria!", ephemeral=True)


# ─────────────────────────────────────────
# CONFIRM per mostra
# ─────────────────────────────────────────

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


# ─────────────────────────────────────────
# COG
# ─────────────────────────────────────────

class CharacterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(
        name="set-gallery",
        description="Imposta il canale dove verranno pubblicate le schede personaggio."
    )
    @discord.app_commands.default_permissions(manage_guild=True)
    @discord.app_commands.guild_only()
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
        description="Apre l'editor per modificare descrizione e colore hex di una scheda."
    )
    @discord.app_commands.describe(personaggio="Nome del personaggio da modificare")
    @discord.app_commands.autocomplete(personaggio=character_autocomplete)
    async def modifica(self, i: discord.Interaction, personaggio: str):
        d = await load_character(i.user.id, personaggio)
        if not d:
            return await i.response.send_message("Personaggio non trovato.", ephemeral=True)

        view = ModificaView(d, i.user.id, self.bot)
        await i.response.send_message(
            embed=create_embed(d),
            view=view,
            ephemeral=True
        )
        view.message = await i.original_response()


async def setup(bot):
    await bot.add_cog(CharacterCog(bot))
