import discord
from discord.ext import commands

ROLE_APPROVER = "Team approvazione"
ROLE_APPROVED = "Pg approvato"


class ApprovalCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def find_role_case_insensitive(self, guild, role_name):
        return discord.utils.find(
            lambda r: r.name.lower() == role_name.lower(),
            guild.roles
        )

    @discord.app_commands.command(
        name="approvazione",
        description="Assegna il ruolo 'Pg approvato' a un utente (solo Team approvazione)"
    )
    async def approvazione(self, interaction: discord.Interaction, user: discord.Member):
        guild = interaction.guild

        # Check that the approver role exists in the server
        approver_role = self.find_role_case_insensitive(guild, ROLE_APPROVER)
        if approver_role is None:
            embed = discord.Embed(
                description=f"Il ruolo **'{ROLE_APPROVER}'** non esiste nel server. Chiedi a un admin di crearlo.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check that the invoking user has the approver role
        if approver_role not in interaction.user.roles:
            embed = discord.Embed(
                description=f"Non hai il ruolo **'{ROLE_APPROVER}'**. Solo i membri del team possono approvare utenti.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check that the approved role exists in the server
        approved_role = self.find_role_case_insensitive(guild, ROLE_APPROVED)
        if approved_role is None:
            embed = discord.Embed(
                description=f"Il ruolo **'{ROLE_APPROVED}'** non esiste nel server. Chiedi a un admin di crearlo.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check that the target user is in the server
        if user not in guild.members:
            embed = discord.Embed(
                description=f"L'utente {user.mention} non è nel server.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if the user already has the approved role
        if approved_role in user.roles:
            embed = discord.Embed(
                description="Questo utente è già stato approvato ;)",
                color=discord.Color.gold()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Assign the approved role
        try:
            await user.add_roles(approved_role)
            embed = discord.Embed(
                description=f"{user.mention} ha ottenuto il ruolo **{approved_role.name}**",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            embed = discord.Embed(
                description=f"Non ho i permessi per assegnare il ruolo. Assicurati che il mio ruolo sia posizionato **sopra** '{ROLE_APPROVED}' nella gerarchia dei ruoli.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                description=str(e),
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ApprovalCog(bot))
