import discord
from discord.ext import commands, tasks
import random
import time

# sessioni per canale
sessions = {}

# Limite massimo partecipanti (embed field max 1024 caratteri)
_MAX_POOL_SIZE = 50
# Timeout sessione in secondi (30 minuti)
_SESSION_TIMEOUT = 30 * 60
# Limite massimo caratteri totali embed Discord
_EMBED_TOTAL_CHAR_LIMIT = 6000
# Soglia di sicurezza (lasciamo 200 di margine)
_EMBED_SAFE_LIMIT = 5800


def build_embed(cid):
    data = sessions.get(cid, {"pool": [], "result": []})

    embed = discord.Embed(
        title="Destino",
        description="Il mazzo e' stato mescolato... il fato osserva in silenzio.",
        color=discord.Color.dark_purple()
    )

    # partecipanti (tronca se troppo lungo)
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

    # Verifica limite totale embed e tronca se necessario
    total_len = len(str(embed.to_dict()))
    if total_len > _EMBED_SAFE_LIMIT and data["pool"]:
        pool_truncated = "\n".join(f"- {p}" for p in data["pool"][:15]) + "\n... e altri"
        if len(pool_truncated) > 900:
            pool_truncated = pool_truncated[:897] + "..."
        embed.clear_fields()
        embed.add_field(name="Partecipanti", value=pool_truncated, inline=False)
        if data["result"]:
            result_text = "\n".join(f"- {r}" for r in data["result"])
            if len(result_text) > 900:
                result_text = result_text[:897] + "..."
            embed.add_field(name="Esito", value=result_text, inline=False)

    return embed


class DestinoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cleanup_task.start()

    def cog_unload(self):
        self.cleanup_task.cancel()

    @tasks.loop(minutes=5)
    async def cleanup_task(self):
        """Pulisce le sessioni scadute ogni 5 minuti."""
        now = time.time()
        stale = [
            cid
            for cid, s in list(sessions.items())
            if now - s.get("_created", now) > _SESSION_TIMEOUT
        ]
        for cid in stale:
            sessions.pop(cid, None)
        if stale:
            print(f"Pulite {len(stale)} sessioni destino scadute.")

    @cleanup_task.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()

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
                "message": None,
                "_created": time.time()
            }

        session = sessions[cid]

        # =====================
        # RESET
        # =====================
        if reset:
            sessions[cid] = {
                "pool": [],
                "result": [],
                "message": None,
                "_created": time.time()
            }
            await interaction.followup.send("Destino resettato.")
            return

        # =====================
        # ADD
        # =====================
        if add:
            names = [
                n.strip()
                for n in add.replace("\n", ",").split(",")
                if n.strip()
            ]
            spazio_rimasto = _MAX_POOL_SIZE - len(session["pool"])
            if spazio_rimasto <= 0:
                await interaction.followup.send(
                    f" Raggiunto il limite massimo di {_MAX_POOL_SIZE} partecipanti.",
                    ephemeral=True
                )
                return
            if len(names) > spazio_rimasto:
                names = names[:spazio_rimasto]
                await interaction.followup.send(
                    f" Aggiunti solo {spazio_rimasto} partecipanti (limite {_MAX_POOL_SIZE}).",
                    ephemeral=True
                )
            session["pool"].extend(names)

        # =====================
        # DRAW
        # =====================
        if draw is not None:
            if draw <= 0:
                await interaction.followup.send(
                    " Il numero da pescare deve essere positivo.",
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
            except (discord.NotFound, discord.HTTPException):
                try:
                    msg = await interaction.followup.send(embed=embed, wait=True)
                    session["message"] = msg
                except (discord.NotFound, discord.HTTPException):
                    sessions.pop(cid, None)
                    await interaction.followup.send(
                        " Sessione scaduta. Usa /destino per ricominciare.",
                        ephemeral=True
                    )


async def setup(bot):
    await bot.add_cog(DestinoCog(bot))
