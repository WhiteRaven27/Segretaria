import discord
from discord.ext import commands
import json
import os
from .character_data import CharacterData, create_embed, load_character, load_all_characters, save_character, delete_character

# Gallery config file
GALLERY_CONFIG_FILE = "data/gallery_config.json"

def load_gallery_config():
    """Carica la configurazione della galleria"""
    if os.path.exists(GALLERY_CONFIG_FILE):
        try:
            with open(GALLERY_CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_gallery_config(config):
    """Salva la configurazione della galleria"""
    os.makedirs("data", exist_ok=True)
    with open(GALLERY_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def get_gallery_channel(guild_id):
    """Ottiene il channel della galleria per un server"""
    config = load_gallery_config()
    return config.get(str(guild_id))

def set_gallery_channel(guild_id, channel_id):
    """Imposta il channel della galleria per un server"""
    config = load_gallery_config()
    config[str(guild_id)] = channel_id
    save_gallery_config(config)

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

        # Non inviare un messaggio di conferma - l'embed aggiornato è la conferma

        await interaction.response.defer()

class EmbedEditor(discord.ui.View):
    def __init__(self, data, message=None, user_id=None, bot=None):
        super().__init__(timeout=None)
        self.data = data
        self.message = message
        self.user_id = user_id
        self.bot = bot

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

    @discord.ui.button(label="Identita", style=discord.ButtonStyle.primary)
    async def identita_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Identita", "identita")

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

    @discord.ui.button(label="Abilita", style=discord.ButtonStyle.success)
    async def abilita_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Abilita Eroiche (opzionale)", "abilita")

    @discord.ui.button(label="Colore", style=discord.ButtonStyle.danger)
    async def hex_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Colore (#FFFFFF)", "hex_color")

    @discord.ui.button(label="Immagine", style=discord.ButtonStyle.danger)
    async def immagine_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.open_modal(interaction, "Link Immagine", "immagine")

    @discord.ui.button(label="Salva", style=discord.ButtonStyle.success)
    async def salva_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        save_character(self.user_id, self.data)
        
        # Prova a pubblicare automaticamente nella galleria se configurata
        if interaction.guild:
            gallery_channel_id = get_gallery_channel(interaction.guild.id)
            if gallery_channel_id and self.bot:
                try:
                    gallery_channel = self.bot.get_channel(gallery_channel_id)
                    if gallery_channel:
                        embed = create_embed(self.data)
                        embed.set_footer(text=f"Creato da {interaction.user.name}#{interaction.user.discriminator}")
                        await gallery_channel.send(
                            content=f"Personaggio aggiornato da {interaction.user.mention}",
                            embed=embed
                        )
                except Exception as e:
                    print(f"Errore nel posting automatico della galleria: {e}")
        
        await interaction.response.send_message(
            f"Personaggio salvato!",
            ephemeral=True
        )

class ConfirmView(discord.ui.View):
    def __init__(self, user, embed):
        super().__init__(timeout=60)
        self.user = user
        self.embed = embed

    @discord.ui.button(label="Si", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message(
                "Non puoi confermare questo personaggio.",
                ephemeral=True
            )
            return

        await interaction.channel.send(
            content=f"Personaggio inviato da {self.user.mention}",
            embed=self.embed
        )

        await interaction.response.edit_message(
            content="Personaggio inviato.",
            view=None,
            embed=None
        )

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message(
                "Non puoi annullare questo personaggio.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content="Invio annullato.",
            view=None,
            embed=None
        )

class ConfirmDeleteView(discord.ui.View):
    def __init__(self, user, character_id=None):
        super().__init__(timeout=60)
        self.user = user
        self.character_id = character_id

    @discord.ui.button(label="Si, elimina", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message(
                "Non puoi eliminare il personaggio di un altro.",
                ephemeral=True
            )
            return

        if delete_character(self.user.id, self.character_id):
            await interaction.response.edit_message(
                content="Personaggio eliminato permanentemente.",
                view=None
            )
        else:
            await interaction.response.send_message(
                "Errore nell'eliminazione del personaggio.",
                ephemeral=True
            )

    @discord.ui.button(label="No, annulla", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message(
                "Non puoi annullare l'eliminazione del personaggio di un altro.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content="Eliminazione annullata.",
            view=None
        )

class CharacterSelectView(discord.ui.View):
    def __init__(self, user, characters, callback):
        super().__init__(timeout=60)
        self.user = user
        self.characters = characters
        self.callback = callback
        
        # Crea un select menu con i personaggi
        options = [
            discord.SelectOption(
                label=char.nome[:100],
                value=char.character_id,
                description=f"ID: {char.character_id}"
            )
            for char in characters
        ]
        
        select = discord.ui.Select(
            placeholder="Scegli un personaggio...",
            options=options
        )
        select.callback = self.on_select
        self.add_item(select)
    
    async def on_select(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message(
                "Non puoi selezionare il personaggio di un altro.",
                ephemeral=True
            )
            return
        
        character_id = interaction.data["values"][0]
        await self.callback(interaction, character_id)

class CharacterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.character_messages = {}  # Per tracciare i messaggi dei personaggi in galleria

    async def post_to_gallery(self, guild_id, user, data):
        """Posta il personaggio nella galleria"""
        gallery_channel_id = get_gallery_channel(guild_id)
        
        if not gallery_channel_id:
            print(f"DEBUG: No gallery channel configured for guild {guild_id}")
            return None
        
        try:
            gallery_channel = self.bot.get_channel(gallery_channel_id)
            if not gallery_channel:
                print(f"DEBUG: Gallery channel {gallery_channel_id} not found")
                return None
            
            embed = create_embed(data)
            embed.set_footer(text=f"Creato da {user.name}#{user.discriminator}")
            
            print(f"DEBUG: Posting character {data.nome} to gallery channel {gallery_channel_id}")
            message = await gallery_channel.send(
                content=f"Nuovo Personaggio da {user.mention}",
                embed=embed
            )
            
            # Salva il message ID per possibili aggiornamenti futuri
            self.character_messages[data.character_id] = message.id
            print(f"DEBUG: Character posted successfully, message ID: {message.id}")
            return message
        except Exception as e:
            print(f"Errore nel posting della galleria: {e}")
            import traceback
            traceback.print_exc()
            return None

    @discord.app_commands.command(name="set-gallery", description="Imposta il channel per la galleria dei personaggi")
    @discord.app_commands.checks.has_permissions(administrator=True)
    async def set_gallery(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Imposta il channel della galleria (solo admin)"""
        set_gallery_channel(interaction.guild.id, channel.id)
        
        embed = discord.Embed(
            title="Galleria Configurata",
            description=f"La galleria dei personaggi e stata impostata su {channel.mention}",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="crea", description="Crea un nuovo personaggio")
    async def crea(self, interaction: discord.Interaction):
        """Crea un nuovo personaggio"""
        data = CharacterData()
        view = EmbedEditor(data, user_id=interaction.user.id, bot=self.bot)

        await interaction.response.send_message(
            embed=create_embed(data),
            view=view,
            ephemeral=True
        )

        message = await interaction.original_response()
        view.message = message

    @discord.app_commands.command(name="modifica", description="Modifica uno dei tuoi personaggi")
    async def modifica(self, interaction: discord.Interaction):
        """Modifica un personaggio salvato"""
        characters = load_all_characters(interaction.user.id)
        
        if not characters:
            await interaction.response.send_message(
                "Non hai personaggi salvati. Usa /crea per crearne uno!",
                ephemeral=True
            )
            return
        
        if len(characters) == 1:
            # Se c'è solo un personaggio, caricalo direttamente
            data = characters[0]
            view = EmbedEditor(data, user_id=interaction.user.id, bot=self.bot)
            
            await interaction.response.send_message(
                embed=create_embed(data),
                view=view,
                ephemeral=True
            )
            
            message = await interaction.original_response()
            view.message = message
        else:
            # Se ce ne sono più, mostra un select menu
            async def on_select(inter, character_id):
                data = load_character(interaction.user.id, character_id)
                view = EmbedEditor(data, user_id=interaction.user.id, bot=self.bot)
                
                await inter.response.send_message(
                    embed=create_embed(data),
                    view=view,
                    ephemeral=True
                )
                
                message = await inter.original_response()
                view.message = message
            
            select_view = CharacterSelectView(interaction.user, characters, on_select)
            await interaction.response.send_message(
                "Quale personaggio vuoi modificare?",
                view=select_view,
                ephemeral=True
            )

    @discord.app_commands.command(name="mostra", description="Mostra uno dei tuoi personaggi salvati")
    async def mostra(self, interaction: discord.Interaction):
        """Mostra un personaggio salvato"""
        characters = load_all_characters(interaction.user.id)
        
        if not characters:
            await interaction.response.send_message(
                "Non hai personaggi salvati. Usa /crea per crearne uno!",
                ephemeral=True
            )
            return
        
        if len(characters) == 1:
            # Se c'è solo un personaggio, mostralo direttamente
            data = characters[0]
            embed = create_embed(data)
            view = ConfirmView(interaction.user, embed)

            await interaction.response.send_message(
                content="Questo va bene?",
                embed=embed,
                view=view,
                ephemeral=True
            )
        else:
            # Se ce ne sono più, mostra un select menu
            async def on_select(inter, character_id):
                data = load_character(interaction.user.id, character_id)
                embed = create_embed(data)
                view = ConfirmView(interaction.user, embed)

                await inter.response.send_message(
                    content="Questo va bene?",
                    embed=embed,
                    view=view,
                    ephemeral=True
                )
            
            select_view = CharacterSelectView(interaction.user, characters, on_select)
            await interaction.response.send_message(
                "Quale personaggio vuoi mostrare?",
                view=select_view,
                ephemeral=True
            )

    @discord.app_commands.command(name="elimina", description="Elimina uno dei tuoi personaggi")
    async def elimina(self, interaction: discord.Interaction):
        """Elimina un personaggio salvato"""
        characters = load_all_characters(interaction.user.id)
        
        if not characters:
            await interaction.response.send_message(
                "Non hai personaggi salvati.",
                ephemeral=True
            )
            return
        
        if len(characters) == 1:
            # Se c'è solo un personaggio, chiedi conferma direttamente
            data = characters[0]
            embed = discord.Embed(
                title="Conferma Eliminazione",
                description=f"Sei sicuro di voler eliminare il personaggio {data.nome}? Questa azione e irreversibile!",
                color=discord.Color.red()
            )

            view = ConfirmDeleteView(interaction.user, data.character_id)
            await interaction.response.send_message(
                embed=embed,
                view=view,
                ephemeral=True
            )
        else:
            # Se ce ne sono più, mostra un select menu
            async def on_select(inter, character_id):
                data = load_character(interaction.user.id, character_id)
                embed = discord.Embed(
                    title="Conferma Eliminazione",
                    description=f"Sei sicuro di voler eliminare il personaggio {data.nome}? Questa azione e irreversibile!",
                    color=discord.Color.red()
                )

                view = ConfirmDeleteView(interaction.user, character_id)
                await inter.response.send_message(
                    embed=embed,
                    view=view,
                    ephemeral=True
                )
            
            select_view = CharacterSelectView(interaction.user, characters, on_select)
            await interaction.response.send_message(
                "Quale personaggio vuoi eliminare?",
                view=select_view,
                ephemeral=True
            )

    @discord.app_commands.command(name="pubblica", description="Pubblica uno dei tuoi personaggi nella galleria")
    async def pubblica(self, interaction: discord.Interaction):
        """Pubblica un personaggio nella galleria"""
        if not interaction.guild:
            await interaction.response.send_message(
                "Questo comando funziona solo in un server!",
                ephemeral=True
            )
            return

        characters = load_all_characters(interaction.user.id)
        
        if not characters:
            await interaction.response.send_message(
                "Non hai personaggi salvati. Usa /crea per crearne uno!",
                ephemeral=True
            )
            return

        gallery_channel_id = get_gallery_channel(interaction.guild.id)
        
        if not gallery_channel_id:
            await interaction.response.send_message(
                "Nessuna galleria configurata. Chiedi a un admin di usare /set-gallery",
                ephemeral=True
            )
            return

        if len(characters) == 1:
            # Se c'è solo un personaggio, pubblicalo direttamente
            data = characters[0]
            message = await self.post_to_gallery(interaction.guild.id, interaction.user, data)
            
            if message:
                await interaction.response.send_message(
                    f"Personaggio pubblicato nella galleria! [Vai al messaggio]({message.jump_url})",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "Errore nel pubblicare il personaggio.",
                    ephemeral=True
                )
        else:
            # Se ce ne sono più, mostra un select menu
            async def on_select(inter, character_id):
                data = load_character(interaction.user.id, character_id)
                message = await self.post_to_gallery(interaction.guild.id, interaction.user, data)
                
                if message:
                    await inter.response.send_message(
                        f"Personaggio pubblicato nella galleria! [Vai al messaggio]({message.jump_url})",
                        ephemeral=True
                    )
                else:
                    await inter.response.send_message(
                        "Errore nel pubblicare il personaggio.",
                        ephemeral=True
                    )
            
            select_view = CharacterSelectView(interaction.user, characters, on_select)
            await interaction.response.send_message(
                "Quale personaggio vuoi pubblicare?",
                view=select_view,
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(CharacterCog(bot))

