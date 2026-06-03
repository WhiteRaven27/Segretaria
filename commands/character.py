import discord
from discord.ext import commands
from .character_data import CharacterData, create_embed, load_character, save_character, delete_character

class EditModal(discord.ui.Modal):
    def __init__(self, title, field_name, data, message, view):
        super().__init__(title=title)

        self.field_name = field_name
        self.data = data
        self.message = message
        self.view_ref = view

        self.input = discord.ui.TextInput(
            label=title,
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )

        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        setattr(self.data, self.field_name, str(self.input))
        save_character(interaction.user.id, self.data)

        await self.message.edit(
            embed=create_embed(self.data),
            view=self.view_ref
        )

        await interaction.response.send_message(
            f"✅ Campo aggiornato: {self.field_name}",
            ephemeral=True
        )

class EmbedEditor(discord.ui.View):
    def __init__(self, data, message=None, user_id=None):
        super().__init__(timeout=None)
        self.data = data
        self.message = message
        self.user_id = user_id

    async def open_modal(self, interaction, title, field_name):
        modal = EditModal(
            title=title,
            field_name=field_name,
            data=self.data,
            message=self.message,
            view=self
        )

        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Nome", style=discord.ButtonStyle.primary)
    async def nome_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Nome", "nome")

    @discord.ui.button(label="Identità", style=discord.ButtonStyle.primary)
    async def identita_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Identità", "identita")

    @discord.ui.button(label="Origine", style=discord.ButtonStyle.primary)
    async def origine_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Origine", "origine")

    @discord.ui.button(label="Tema", style=discord.ButtonStyle.secondary)
    async def tema_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Tema", "tema")

    @discord.ui.button(label="Descrizione", style=discord.ButtonStyle.secondary)
    async def descrizione_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Descrizione", "descrizione")

    @discord.ui.button(label="Classe", style=discord.ButtonStyle.success)
    async def classe_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Classe", "classe")

    @discord.ui.button(label="Abilità", style=discord.ButtonStyle.success)
    async def abilita_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Abilità Eroiche", "abilita")

    @discord.ui.button(label="Hex Color", style=discord.ButtonStyle.danger)
    async def hex_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Hex Color (#FFFFFF)", "hex_color")

    @discord.ui.button(label="Immagine", style=discord.ButtonStyle.danger)
    async def immagine_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Link Immagine", "immagine")

    @discord.ui.button(label="Salva Personaggio", style=discord.ButtonStyle.success)
    async def salva_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        save_character(self.user_id, self.data)
        await interaction.response.send_message(
            f"✅ Personaggio salvato!",
            ephemeral=True
        )

class ConfirmView(discord.ui.View):
    def __init__(self, user, embed):
        super().__init__(timeout=60)
        self.user = user
        self.embed = embed

    @discord.ui.button(label="Sì", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message(
                "❌ Non puoi confermare questo personaggio.",
                ephemeral=True
            )
            return

        await interaction.channel.send(
            content=f"📢 Personaggio inviato da {self.user.mention}",
            embed=self.embed
        )

        await interaction.response.edit_message(
            content="✅ Personaggio inviato.",
            view=None,
            embed=None
        )

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message(
                "❌ Non puoi annullare questo personaggio.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content="❌ Invio annullato.",
            view=None,
            embed=None
        )

class ConfirmDeleteView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=60)
        self.user = user

    @discord.ui.button(label="Sì, elimina", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message(
                "❌ Non puoi eliminare il personaggio di un altro.",
                ephemeral=True
            )
            return

        if delete_character(self.user.id):
            await interaction.response.edit_message(
                content="🗑️ Personaggio eliminato permanentemente.",
                view=None
            )
        else:
            await interaction.response.send_message(
                "❌ Errore nell'eliminazione del personaggio.",
                ephemeral=True
            )

    @discord.ui.button(label="No, annulla", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message(
                "❌ Non puoi annullare l'eliminazione del personaggio di un altro.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content="❌ Eliminazione annullata.",
            view=None
        )

class CharacterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="crea", description="Crea un nuovo personaggio")
    async def crea(self, interaction: discord.Interaction):
        """Crea un nuovo personaggio"""
        data = CharacterData()
        view = EmbedEditor(data, user_id=interaction.user.id)

        message = await interaction.response.send_message(
            embed=create_embed(data),
            view=view,
            ephemeral=True
        )

        view.message = await interaction.original_response()

    @discord.app_commands.command(name="modifica", description="Modifica il tuo personaggio")
    async def modifica(self, interaction: discord.Interaction):
        """Modifica il personaggio salvato"""
        data = load_character(interaction.user.id)
        
        if data is None:
            await interaction.response.send_message(
                "❌ Non hai un personaggio salvato. Usa `/crea` per crearne uno!",
                ephemeral=True
            )
            return

        view = EmbedEditor(data, user_id=interaction.user.id)
        message = await interaction.response.send_message(
            embed=create_embed(data),
            view=view,
            ephemeral=True
        )

        view.message = await interaction.original_response()

    @discord.app_commands.command(name="mostra", description="Mostra il tuo personaggio salvato")
    async def mostra(self, interaction: discord.Interaction):
        """Mostra il personaggio salvato"""
        data = load_character(interaction.user.id)
        
        if data is None:
            await interaction.response.send_message(
                "❌ Non hai un personaggio salvato. Usa `/crea` per crearne uno!",
                ephemeral=True
            )
            return

        embed = create_embed(data)
        view = ConfirmView(interaction.user, embed)

        await interaction.response.send_message(
            content="Questo va bene?",
            embed=embed,
            view=view,
            ephemeral=True
        )

    @discord.app_commands.command(name="elimina", description="Elimina il tuo personaggio")
    async def elimina(self, interaction: discord.Interaction):
        """Elimina il personaggio salvato"""
        data = load_character(interaction.user.id)
        
        if data is None:
            await interaction.response.send_message(
                "❌ Non hai un personaggio salvato.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="⚠️ Conferma Eliminazione",
            description=f"Sei sicuro di voler eliminare il personaggio **{data.nome}**? Questa azione è irreversibile!",
            color=discord.Color.red()
        )

        view = ConfirmDeleteView(interaction.user)
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(CharacterCog(bot))
