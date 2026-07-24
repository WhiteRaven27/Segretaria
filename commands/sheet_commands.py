import asyncio
import discord
from discord.ext import commands

from .character_data import (
    CharacterData,
    create_embed,
    load_character,
    load_all_characters,
    save_character,
    delete_character,
    validate_character_id,
)
from .message_owners_store import save_message_owners
from .sheet import extract_sheet_id, fetch_csv, parse_character

# ─────────────────────────────────────────
# Autocomplete
# ─────────────────────────────────────────

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
# Show confirm view
# ─────────────────────────────────────────

class ShowConfirm(discord.ui.View):
    def __init__(self, user, embed, bot):
        super().__init__(timeout=60)
        self.user = user
        self.embed = embed
        self.bot = bot

    @discord.ui.button(label="SI", style=discord.ButtonStyle.success)
    async def si(self, i: discord.Interaction, b):
        if i.user != self.user:
            await i.response.defer()
            return

        msg = await i.channel.send(
            content=f"Scheda di {self.user.mention}",
            embed=self.embed,
        )

        self.bot.message_owners[msg.id] = self.user.id
        await save_message_owners(self.bot.message_owners)

        await i.response.edit_message(content="Pubblicato.", view=None)

    @discord.ui.button(label="NO", style=discord.ButtonStyle.danger)
    async def no(self, i: discord.Interaction, b):
        await i.response.edit_message(content="Annullato.", view=None)


# ─────────────────────────────────────────
# Confirm delete view
# ─────────────────────────────────────────

class ConfirmDelete(discord.ui.View):
    def __init__(self, user, cid):
        super().__init__(timeout=30)
        self.user = user
        self.cid = cid

    @discord.ui.button(label="SI", style=discord.ButtonStyle.danger)
    async def si(self, i: discord.Interaction, b):
        if i.user != self.user:
            await i.response.defer()
            return

        if not validate_character_id(self.cid):
            await i.response.edit_message(content="ID personaggio non valido.", view=None)
            return

        await delete_character(i.user.id, self.cid)
        await i.response.edit_message(content="Personaggio eliminato.", view=None)

    @discord.ui.button(label="NO", style=discord.ButtonStyle.secondary)
    async def no(self, i: discord.Interaction, b):
        await i.response.edit_message(content="Operazione annullata.", view=None)


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

def _apply_sheet_data(char: CharacterData, data: dict) -> None:
    """Write parsed sheet fields onto a CharacterData object."""
    char.nome     = data["nome"]
    char.livello  = data["livello"]
    char.identita = data["identita"]
    char.tema     = data["tema"]
    char.origine  = data["origine"]
    char.classe   = data["classe"]
    char.abilita  = data["abilita"]
    char.immagine = data["immagine"]


# ─────────────────────────────────────────
# Cog
# ─────────────────────────────────────────

class SheetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── /link ─────────────────────────────

    @discord.app_commands.command(
        name="link",
        description="Collega il tuo Google Sheet al bot e crea la scheda personaggio."
    )
    @discord.app_commands.describe(url="Link al tuo Google Sheet personaggio")
    async def link(self, i: discord.Interaction, url: str):
        await i.response.defer(ephemeral=True)

        sheet_id = extract_sheet_id(url)
        if not sheet_id:
            await i.followup.send(
                "Link non valido. Incolla l'URL del Google Sheet dal browser.",
                ephemeral=True,
            )
            return

        try:
            csv_text = await fetch_csv(sheet_id)
        except ValueError as e:
            await i.followup.send(str(e), ephemeral=True)
            return

        data = parse_character(csv_text)

        # Check if user already has a character with this name → update it
        existing = await load_all_characters(i.user.id)
        char = next((c for c in existing if c.nome == data["nome"]), None)

        if char is None:
            char = CharacterData()

        _apply_sheet_data(char, data)
        char.sheet_url = url

        try:
            await save_character(i.user.id, char)
        except Exception as e:
            print(f"❌ Errore salvataggio: {e}")
            await i.followup.send("Errore nel salvataggio della scheda.", ephemeral=True)
            return

        await i.followup.send(
            f"✅ Scheda di **{char.nome}** collegata con successo!\n"
            "Usa `/update` per aggiornare i dati dal foglio in futuro.",
            embed=create_embed(char),
            ephemeral=True,
        )

    # ── /update ───────────────────────────

    @discord.app_commands.command(
        name="update",
        description="Aggiorna la scheda dal Google Sheet collegato."
    )
    @discord.app_commands.describe(personaggio="Nome del personaggio da aggiornare")
    @discord.app_commands.autocomplete(personaggio=character_autocomplete)
    async def update(self, i: discord.Interaction, personaggio: str = None):
        await i.response.defer(ephemeral=True)

        if personaggio:
            char = await load_character(i.user.id, personaggio)
        else:
            chars = await load_all_characters(i.user.id)
            char = chars[0] if len(chars) == 1 else None
            if char is None and chars:
                await i.followup.send(
                    "Hai più personaggi. Specifica quale aggiornare con l'autocomplete.",
                    ephemeral=True,
                )
                return

        if not char:
            await i.followup.send(
                "Nessun personaggio trovato. Usa `/link` per collegarne uno.",
                ephemeral=True,
            )
            return

        if not char.sheet_url:
            await i.followup.send(
                "Questo personaggio non ha un Google Sheet collegato. Usa `/link` prima.",
                ephemeral=True,
            )
            return

        sheet_id = extract_sheet_id(char.sheet_url)
        if not sheet_id:
            await i.followup.send("URL del foglio non valido.", ephemeral=True)
            return

        try:
            csv_text = await fetch_csv(sheet_id)
        except ValueError as e:
            await i.followup.send(str(e), ephemeral=True)
            return

        data = parse_character(csv_text)
        _apply_sheet_data(char, data)

        try:
            await save_character(i.user.id, char)
        except Exception as e:
            print(f"❌ Errore aggiornamento: {e}")
            await i.followup.send("Errore nel salvataggio.", ephemeral=True)
            return

        await i.followup.send(
            f"✅ **{char.nome}** aggiornato!",
            embed=create_embed(char),
            ephemeral=True,
        )

    # ── /mostra ───────────────────────────

    @discord.app_commands.command(
        name="mostra",
        description="Mostra la tua scheda personaggio nel canale corrente."
    )
    @discord.app_commands.describe(personaggio="Nome del personaggio da mostrare")
    @discord.app_commands.autocomplete(personaggio=character_autocomplete)
    async def mostra(self, i: discord.Interaction, personaggio: str = None):
        if personaggio:
            char = await load_character(i.user.id, personaggio)
        else:
            chars = await load_all_characters(i.user.id)
            char = chars[0] if len(chars) == 1 else None
            if char is None and chars:
                return await i.response.send_message(
                    "Hai più personaggi. Specifica quale mostrare.",
                    ephemeral=True,
                )

        if not char:
            return await i.response.send_message(
                "Nessun personaggio trovato. Usa `/link` per collegarne uno.",
                ephemeral=True,
            )

        embed = create_embed(char)
        await i.response.send_message(
            "Vuoi mostrare questa scheda?",
            embed=embed,
            view=ShowConfirm(i.user, embed, self.bot),
            ephemeral=True,
        )

    # ── /elimina ──────────────────────────

    @discord.app_commands.command(
        name="elimina",
        description="Elimina un personaggio dal bot."
    )
    @discord.app_commands.describe(personaggio="Nome del personaggio da eliminare")
    @discord.app_commands.autocomplete(personaggio=character_autocomplete)
    async def elimina(self, i: discord.Interaction, personaggio: str):
        char = await load_character(i.user.id, personaggio)

        if not char:
            return await i.response.send_message(
                "Personaggio non trovato.", ephemeral=True
            )

        await i.response.send_message(
            embed=discord.Embed(
                title="Conferma eliminazione",
                description=char.nome,
                color=discord.Color.red(),
            ),
            view=ConfirmDelete(i.user, char.character_id),
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(SheetCog(bot))
