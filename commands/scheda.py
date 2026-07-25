import asyncio
import discord
from discord.ext import commands

from . import sheet
from .character_data import (
    CharacterData,
    create_embed,
    save_character,
    delete_character,
    read_all,
    load_character,
    save_message_owners,
)
from .character import character_autocomplete
from .gallery_store import get_gallery_channel


# ─────────────────────────────────────────
# Confirm Delete View
# ─────────────────────────────────────────

class ConfirmDeleteView(discord.ui.View):
    def __init__(self, user, found_cid, found_name):
        super().__init__(timeout=30)
        self.user = user
        self.found_cid = found_cid
        self.found_name = found_name

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="SI", style=discord.ButtonStyle.danger)
    async def si(self, i: discord.Interaction, b):
        if i.user != self.user:
            await i.response.defer()
            return
        await delete_character(i.user.id, self.found_cid)
        await i.response.edit_message(
            content=f"Scheda **{self.found_name}** eliminata.",
            view=None
        )

    @discord.ui.button(label="NO", style=discord.ButtonStyle.secondary)
    async def no(self, i: discord.Interaction, b):
        await i.response.edit_message(
            content="Operazione annullata.",
            view=None
        )


# ─────────────────────────────────────────
# Cog
# ─────────────────────────────────────────

class SchedaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(
        name="scheda",
        description="Carica una scheda da Google Sheets e la salva."
    )
    @discord.app_commands.describe(
        url="URL del foglio Google Sheets (condivisione pubblica obbligatoria)"
    )
    async def scheda(
        self,
        interaction: discord.Interaction,
        url: str,
    ):
        await interaction.response.defer(ephemeral=True)

        # 1. Extract sheet ID
        sheet_id = sheet.extract_sheet_id(url)
        if not sheet_id:
            return await interaction.followup.send(
                "URL non valido. Assicurati di aver copiato l'intero link del foglio Google Sheets.",
                ephemeral=True
            )

        # 2. Fetch CSV
        try:
            csv_text = await sheet.fetch_csv(sheet_id)
        except ValueError as e:
            return await interaction.followup.send(str(e), ephemeral=True)
        except Exception as e:
            return await interaction.followup.send(
                "Errore durante il download: " + str(e),
                ephemeral=True
            )

        # 3. Parse
        try:
            parsed = sheet.parse_character(csv_text)
        except Exception as e:
            return await interaction.followup.send(
                "Errore durante il parsing della scheda: " + str(e),
                ephemeral=True
            )

        # 4. Validate parsed data (CSV vuoto o non valido)
        nome = parsed.get("nome", "Sconosciuto")
        identita = parsed.get("identita", "\u2014")
        origine = parsed.get("origine", "\u2014")

        if nome == "Sconosciuto" or (identita == "\u2014" and origine == "\u2014"):
            return await interaction.followup.send(
                "Il foglio Google Sheets non contiene una scheda valida. "
                "Assicurati che il foglio abbia la struttura standard di Fabula Ultima "
                "(almeno Nome e Identit\u00e0 o Origine compilati).",
                ephemeral=True
            )

        # 5. Build CharacterData
        data = CharacterData()
        data.nome = nome
        data.identita = identita
        data.origine = origine
        data.tema = parsed.get("tema", "\u2014")
        data.livello = parsed.get("livello", "\u2014")
        data.classe = parsed.get("classe", "\u2014")
        data.abilita = parsed.get("abilita", "")
        data.immagine = parsed.get("immagine", None)
        data.link = url

        # 6. Check if URL already exists for this user
        all_data = await read_all()
        user_data = all_data.get(str(interaction.user.id), {})
        url_clean = url.strip().rstrip("/")
        for cid, raw in user_data.items():
            if raw.get("link", "").strip().rstrip("/") == url_clean:
                return await interaction.followup.send(
                    "Scheda gi\u00e0 presente, usa il comando /aggiorna.",
                    ephemeral=True
                )

        # 7. Save
        try:
            await save_character(interaction.user.id, data)
        except Exception as e:
            return await interaction.followup.send(
                "Errore nel salvataggio: " + str(e),
                ephemeral=True
            )

        # 8. Post to gallery if configured
        async def post_gallery():
            try:
                if not interaction.guild:
                    return
                cid = await get_gallery_channel(interaction.guild.id)
                if not cid:
                    return
                ch = self.bot.get_channel(cid)
                if ch:
                    msg = await ch.send(
                        content="Scheda di " + interaction.user.mention,
                        embed=create_embed(data)
                    )
                    # Traccia per permettere cancellazione con reazione X
                    self.bot.message_owners[msg.id] = interaction.user.id
                    await save_message_owners(self.bot.message_owners)
            except Exception as e:
                print("Errore nel post gallery:", e)

        asyncio.create_task(post_gallery())

        # 9. Ephemeral confirmation only (embed goes only to gallery)
        await interaction.followup.send("Scheda caricata.", ephemeral=True)

    @discord.app_commands.command(
        name="aggiorna",
        description="Aggiorna una scheda personaggio rileggendo i dati dal foglio Google Sheets."
    )
    @discord.app_commands.describe(
        personaggio="Nome del personaggio da aggiornare"
    )
    @discord.app_commands.autocomplete(personaggio=character_autocomplete)
    async def aggiorna(
        self,
        interaction: discord.Interaction,
        personaggio: str,
    ):
        await interaction.response.defer(ephemeral=True)

        existing = await load_character(interaction.user.id, personaggio)
        if not existing:
            return await interaction.followup.send(
                "Personaggio non trovato.",
                ephemeral=True
            )

        url = existing.link
        if not url:
            return await interaction.followup.send(
                "Questo personaggio non ha un link Google Sheets associato. Impossibile aggiornare.",
                ephemeral=True
            )

        sheet_id = sheet.extract_sheet_id(url)
        if not sheet_id:
            return await interaction.followup.send(
                "URL del foglio non valido salvato nella scheda.",
                ephemeral=True
            )

        try:
            csv_text = await sheet.fetch_csv(sheet_id)
        except ValueError as e:
            return await interaction.followup.send(str(e), ephemeral=True)
        except Exception as e:
            return await interaction.followup.send(
                "Errore durante il download: " + str(e),
                ephemeral=True
            )

        try:
            parsed = sheet.parse_character(csv_text)
        except Exception as e:
            return await interaction.followup.send(
                "Errore durante il parsing della scheda: " + str(e),
                ephemeral=True
            )

        nome = parsed.get("nome", "Sconosciuto")
        identita = parsed.get("identita", "\u2014")
        origine = parsed.get("origine", "\u2014")

        if nome == "Sconosciuto" or (identita == "\u2014" and origine == "\u2014"):
            return await interaction.followup.send(
                "Il foglio Google Sheets non contiene dati validi. Aggiornamento annullato.",
                ephemeral=True
            )

        existing.nome = nome
        existing.identita = identita
        existing.origine = origine
        existing.tema = parsed.get("tema", existing.tema)
        existing.livello = parsed.get("livello", existing.livello)
        existing.classe = parsed.get("classe", existing.classe)
        existing.abilita = parsed.get("abilita", existing.abilita)
        existing.immagine = parsed.get("immagine", existing.immagine)

        try:
            await save_character(interaction.user.id, existing)
        except Exception as e:
            return await interaction.followup.send(
                "Errore nel salvataggio: " + str(e),
                ephemeral=True
            )

        async def post_gallery():
            try:
                if not interaction.guild:
                    return
                cid = await get_gallery_channel(interaction.guild.id)
                if not cid:
                    return
                ch = self.bot.get_channel(cid)
                if ch:
                    msg = await ch.send(
                        content="Scheda aggiornata di " + interaction.user.mention,
                        embed=create_embed(existing)
                    )
                    # Traccia per permettere cancellazione con reazione X
                    self.bot.message_owners[msg.id] = interaction.user.id
                    await save_message_owners(self.bot.message_owners)
            except Exception as e:
                print("Errore nel post gallery:", e)

        asyncio.create_task(post_gallery())

        await interaction.followup.send("Scheda aggiornata.", ephemeral=True)

    @discord.app_commands.command(
        name="elimina-scheda",
        description="Elimina una scheda personaggio."
    )
    @discord.app_commands.describe(
        personaggio="Nome del personaggio da eliminare"
    )
    @discord.app_commands.autocomplete(personaggio=character_autocomplete)
    async def elimina(
        self,
        interaction: discord.Interaction,
        personaggio: str,
    ):
        await interaction.response.defer(ephemeral=True)

        existing = await load_character(interaction.user.id, personaggio)
        if not existing:
            return await interaction.followup.send(
                "Personaggio non trovato.",
                ephemeral=True
            )

        embed_msg = discord.Embed(
            title="Conferma eliminazione",
            description="Eliminare **" + existing.nome + "**?",
            color=discord.Color.red()
        )

        view = ConfirmDeleteView(interaction.user, existing.character_id, existing.nome)

        await interaction.followup.send(
            embed=embed_msg,
            view=view,
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(SchedaCog(bot))
