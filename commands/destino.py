import discord
from discord.ext import commands
import random

sessions = {}


def build_embed(cid):
    data = sessions.get(cid, {"pool": [], "result": []})

    pool = data["pool"]
    result = data["result"]

    embed = discord.Embed(
        title="Destino",
        color=discord.Color.dark_purple()
    )

    embed.add_field(
        name="Partecipanti",
        value="\n".join(f"- {p}" for p in pool) if pool else "Nessuno",
        inline=False
    )

    if result:
        embed.add_field(
            name="Esito",
            value="\n".join(f"- {r}" for r in result),
            inline=False
        )

    return embed


class DestinoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(
        name="destino",
        description="Gestisce una sessione di estrazione narrativa"
    )
    async def destino(
        self,
        interaction: discord.Interaction,
        add: str = None,
        draw: int = None,
        reset: bool = False
    ):

        cid = interaction.channel.id

        if cid not in sessions:
            sessions[cid] = {"pool": [], "result": [], "message": None}

        session = sessions[cid]

        # RESET
        if reset:
            sessions[cid] = {"pool": [], "result": [], "message": None}

            return await interaction.response.send_message(
                "Destino resettato.",
                ephemeral=True
            )

        # ADD MULTI
        if add:
            names = [n.strip() for n in add.replace(",", " ").split() if n.strip()]
            session["pool"].extend(names)

        # DRAW + END SESSION
        if draw:
            if draw > len(session["pool"]):
                return await interaction.response.send_message(
                    "Non ci sono abbastanza partecipanti nel destino.",
                    ephemeral=True
                )

            winners = random.sample(session["pool"], draw)
            session["result"] = winners

            embed = build_embed(cid)

            await interaction.response.send_message(embed=embed)

            sessions.pop(cid, None)
            return

        # LIVE UPDATE
        embed = build_embed(cid)

        if session["message"] is None:
            await interaction.response.send_message(embed=embed)
            session["message"] = await interaction.original_response()
        else:
            await session["message"].edit(embed=embed)
            await interaction.response.defer()


async def setup(bot):
    await bot.add_cog(DestinoCog(bot))
