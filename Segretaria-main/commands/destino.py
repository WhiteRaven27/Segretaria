import discord
from discord.ext import commands
import random

# sessioni per canale
sessions = {}


def build_embed(cid):
    data = sessions.get(cid, {"pool": [], "result": []})

    embed = discord.Embed(
        title="🎴 Destino",
        description="Il mazzo è stato mescolato... il fato osserva in silenzio.",
        color=discord.Color.dark_purple()
    )

    # partecipanti
    embed.add_field(
        name="Partecipanti",
        value="\n".join(f"- {p}" for p in data["pool"]) if data["pool"] else "Nessuno",
        inline=False
    )

    # esito
    if data["result"]:
        embed.add_field(
            name="Esito",
            value="\n".join(f"- {r}" for r in data["result"]),
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
            names = [
                n.strip()
                for n in add.replace(",", " ").split()
                if n.strip()
            ]
            session["pool"].extend(names)

        # =====================
        # DRAW
        # =====================
        if draw:
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
            msg = await interaction.followup.send(embed=embed)
            session["message"] = msg
        else:
            await session["message"].edit(embed=embed)
            await interaction.followup.send("Aggiornato.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(DestinoCog(bot))