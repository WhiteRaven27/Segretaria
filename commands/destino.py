import discord
from discord.ext import commands
import random

# sessioni per canale
sessions = {}

# Limite massimo partecipanti (embed field max 1024 caratteri)
_MAX_POOL_SIZE = 50


def build_embed(cid):
    data = sessions.get(cid, {"pool": [], "result": []})

    embed = discord.Embed(
        title="🎴 Destino",
        description="Il mazzo è stato mescolato... il fato osserva in silenzio.",
        color=discord.Color.dark_purple()
    )

    # partecipanti (tronca se troppo lungo per evitare 400 Bad Request)
    pool_text = "\n".join(f"- {p}" for p in data["pool"]) if data["pool"] else "Nessuno"
    if len(pool_text) > 1024:
        pool_text = pool_text[:1021] + "..."

    embed.add_field(
        name="Partecipanti",
        value=pool_text,
        inline=False
    )

    # esito
    if data["result"]:
        result_text = "\n".join(f"- {r}" for r in data["result"])
        if len(result_text) > 1024:
            result_text = result_text[:1021] + "..."
        embed.add_field(
            name="Esito",
            value=result_text,
            inline=False
        )

    return embed


class DestinoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(
        name="destino",
        description="Pesca una carta dal tuo destino, come in un duello leggendario."
    )
    async def destino(
        self,
        interaction: discord.Interaction,
        add: str = None,
        draw: int = None,
        reset: bool = False
    ):
        if interaction.channel is None:
            await interaction.response.send_message(
                "Questo comando non funziona qui.", ephemeral=True
            )
            return

        await interaction.response.defer()

        cid = interaction.channel.id

        if cid not in sessions:
            sessions[cid] = {
                "pool": [],
                "result": [],
                "message": None
            }

        session = sessions[cid]

        # =====================
        # RESET
        # =====================
        if reset:
            sessions[cid] = {
                "pool": [],
                "result": [],
                "message": None
            }
            await interaction.followup.send("🎴 Destino resettato.")
            return

        # =====================
        # ADD
        # =====================
        if add:
            # Usa virgola O newline come separatore, NON divide per spazi
            # così i nomi composti (es. "Mario Rossi") restano interi
            names = [
                n.strip()
                for n in add.replace("\n", ",").split(",")
                if n.strip()
            ]
            # Limita il pool totale
            spazio_rimasto = _MAX_POOL_SIZE - len(session["pool"])
            if spazio_rimasto <= 0:
                await interaction.followup.send(
                    f"⚠️ Raggiunto il limite massimo di {_MAX_POOL_SIZE} partecipanti.",
                    ephemeral=True
                )
                return
            if len(names) > spazio_rimasto:
                names = names[:spazio_rimasto]
                await interaction.followup.send(
                    f"⚠️ Aggiunti solo {spazio_rimasto} partecipanti (limite {_MAX_POOL_SIZE}).",
                    ephemeral=True
                )
            session["pool"].extend(names)

        # =====================
        # DRAW
        # =====================
        if draw is not None:
            if draw <= 0:
                await interaction.followup.send(
                    "❌ Il numero da pescare deve essere positivo.",
                    ephemeral=True
                )
                return
            if draw > len(session["pool"]):
                await interaction.followup.send(
                    "Non ci sono abbastanza partecipanti nel mazzo del destino.",
                    ephemeral=True
                )
                return

            winners = random.sample(session["pool"], draw)
            session["result"] = winners

            embed = build_embed(cid)

            await interaction.followup.send(embed=embed)

            # chiude sessione
            sessions.pop(cid, None)
            return

        # =====================
        # UPDATE EMBED
        # =====================
        embed = build_embed(cid)

        if session["message"] is None:
            msg = await interaction.followup.send(embed=embed, wait=True)
            session["message"] = msg
        else:
            try:
                await session["message"].edit(embed=embed)
                await interaction.followup.send("Aggiornato.", ephemeral=True)
            except discord.NotFound:
                # Messaggio originale eliminato o token scaduto (>15 min)
                msg = await interaction.followup.send(embed=embed, wait=True)
                session["message"] = msg


async def setup(bot):
    await bot.add_cog(DestinoCog(bot))
