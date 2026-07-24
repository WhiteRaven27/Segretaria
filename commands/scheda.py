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
)
from .character import character_autocomplete
from .gallery_store import get_gallery_channel


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
                "❌ URL non valido. Assicurati di aver copiato l'intero link del foglio Google Sheets.",
                ephemeral=True
            )

        # 2. Fetch CSV
        try:
            csv_text = await sheet.fetch_csv(sheet_id)
        except ValueError as e:
            return await interaction.followup.send(f"❌ {str(e)}", ephemeral=True)
        except Exception as e:
            return await interaction.followup.send(
                f"❌ Errore durante il download: {str(e)}",
                ephemeral=True
            )

        # 3. Parse
        try:
            parsed = sheet.parse_character(csv_text)
        except Exception as e:
            return await interaction.followup.send(
                f"❌ Errore durante il parsing della scheda: {str(e)}",
                ephemeral=True
            )

        # 4. Build CharacterData
        data = CharacterData()
        data.nome = parsed.get("nome", "Sconosciuto")
        data.identita = parsed.get("identita", "—")
        data.origine = parsed.get("origine", "—")
        data.tema = parsed.get("tema", "—")
        data.classe = parsed.get("classe", "—")
        data.abilita = parsed.get("abilita", "")
        data.immagine = parsed.get("immagine", None)
        data.link = url

        livello = parsed.get("livello", "—")
        data.descrizione = f"Livello: {livello}"

        # 5. Check if URL already exists for this user
        all_data = await read_all()
        user_data = all_data.get(str(interaction.user.id), {})
        url_clean = url.strip().rstrip("/")
        for cid, raw in user_data.items():
            if raw.get("link", "").strip().rstrip("/") == url_clean:
                return await interaction.followup.send(
                    "⚠️ Scheda già presente, usa il comando /aggiorna.",
                    ephemeral=True
                )

        # 6. Save
        try:
            await save_character(interaction.user.id, data)
        except Exception as e:
            return await interaction.followup.send(
                f"❌ Errore nel salvataggio: {str(e)}",
                ephemeral=True
            )

        # 7. Post to gallery if configured
        async def post_gallery():
            try:
                if not interaction.guild:
                    return
                cid = await get_gallery_channel(interaction.guild.id)
                if not cid:
                    return
                ch = self.bot.get_channel(cid)
                if ch:
                    await ch.send(
                        content=f"Scheda di {interaction.user.mention}",
                        embed=create_embed(data)
                    )
            except Exception as e:
                print(f"❌ Errore nel post gallery: {e}")

        asyncio.create_task(post_gallery())

        # 8. Ephemeral confirmation only (embed goes only to gallery)
        await interaction.followup.send("✅ Scheda caricata.", ephemeral=True)

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

        # 1. Load existing character
        existing = await load_character(interaction.user.id, personaggio)
        if not existing:
            return await interaction.followup.send(
                "❌ Personaggio non trovato.",
                ephemeral=True
            )

        # 2. Get the sheet URL
        url = existing.link
        if not url:
            return await interaction.followup.send(
                "❌ Questo personaggio non ha un link Google Sheets associato. Impossibile aggiornare.",
                ephemeral=True
            )

        # 3. Extract sheet ID
        sheet_id = sheet.extract_sheet_id(url)
        if not sheet_id:
            return await interaction.followup.send(
                "❌ URL del foglio non valido salvato nella scheda.",
                ephemeral=True
            )

        # 4. Fetch CSV
        try:
            csv_text = await sheet.fetch_csv(sheet_id)
        except ValueError as e:
            return await interaction.followup.send(f"❌ {str(e)}", ephemeral=True)
        except Exception as e:
            return await interaction.followup.send(
                f"❌ Errore durante il download: {str(e)}",
                ephemeral=True
            )

        # 5. Parse
        try:
            parsed = sheet.parse_character(csv_text)
        except Exception as e:
            return await interaction.followup.send(
                f"❌ Errore durante il parsing della scheda: {str(e)}",
                ephemeral=True
            )

        # 6. Update character data from sheet (preserve character_id, link, hex_color)
        existing.nome = parsed.get("nome", existing.nome)
        existing.identita = parsed.get("identita", existing.identita)
        existing.origine = parsed.get("origine", existing.origine)
        existing.tema = parsed.get("tema", existing.tema)
        existing.classe = parsed.get("classe", existing.classe)
        existing.abilita = parsed.get("abilita", existing.abilita)
        existing.immagine = parsed.get("immagine", existing.immagine)

        livello = parsed.get("livello", "—")
        existing.descrizione = f"Livello: {livello}"

        # 7. Save
        try:
            await save_character(interaction.user.id, existing)
        except Exception as e:
            return await interaction.followup.send(
                f"❌ Errore nel salvataggio: {str(e)}",
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
                    await ch.send(
                        content=f"Scheda aggiornata di {interaction.user.mention}",
                        embed=create_embed(existing)
                    )
            except Exception as e:
                print(f"❌ Errore nel post gallery: {e}")

        asyncio.create_task(post_gallery())

        # 9. Ephemeral confirmation only (embed goes only to gallery)
        await interaction.followup.send("✅ Scheda aggiornata.", ephemeral=True)

    @discord.app_commands.command(
        name="elimina",
        description="Elimina la scheda caricata da un URL di Google Sheets."
    )
    @discord.app_commands.describe(
        url="URL del foglio Google Sheets usato per caricare la scheda"
    )
    async def elimina(
        self,
        interaction: discord.Interaction,
        url: str,
    ):
        await interaction.response.defer(ephemeral=True)

        all_data = await read_all()
        user_data = all_data.get(str(interaction.user.id), {})

        url_clean = url.strip().rstrip("/")

        found_cid = None
        found_name = None
        for cid, raw in user_data.items():
            if raw.get("link", "").strip().rstrip("/") == url_clean:
                found_cid = cid
                found_name = raw.get("nome", "Sconosciuto")
                break

        if not found_cid:
            return await interaction.followup.send(
                "❌ Nessuna scheda trovata per questo URL.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="Conferma eliminazione",
            description=f"Eliminare **{found_name}**?",
            color=discord.Color.red()
        )

        view = discord.ui.View(timeout=30)

        async def si_handler(i: discord.Interaction):
            if i.user != interaction.user:
                await i.response.defer()
                return
            await delete_character(i.user.id, found_cid)
            await i.response.edit_message(
                content=f"✅ Scheda **{found_name}** eliminata.",
                view=None
            )

        async def no_handler(i: discord.Interaction):
            await i.response.edit_message(
                content="Operazione annullata.",
                view=None
            )

        si_btn = discord.ui.Button(label="SI", style=discord.ButtonStyle.danger)
        no_btn = discord.ui.Button(label="NO", style=discord.ButtonStyle.secondary)

        si_btn.callback = si_handler
        no_btn.callback = no_handler

        view.add_item(si_btn)
        view.add_item(no_btn)

        await interaction.followup.send(
            embed=embed,
            view=view,
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(SchedaCog(bot))
