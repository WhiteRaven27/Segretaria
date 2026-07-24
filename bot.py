import os
import asyncio
import logging
import traceback

from dotenv import load_dotenv
import discord
from discord.ext import commands

# =========================
# CONFIG
# =========================

load_dotenv()

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")

# =========================
# DATA
# =========================

os.makedirs("data", exist_ok=True)

from commands.message_owners_store import load_message_owners, save_message_owners

# =========================
# BOT
# =========================

intents = discord.Intents.default()
# Nota: intents.members NON abilitato per evitare crash all'avvio
# (il bot richiederebbe Server Members Intent nel Developer Portal)
# on_raw_reaction_add fornisce già payload.member via API

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# Track message owners for delete reaction (message_id: user_id)
bot.message_owners = load_message_owners()

# =========================
# ERROR HANDLING
# =========================

@bot.event
async def on_error(event, *args, **kwargs):
    print(f"\n❌ ERRORE EVENTO: {event}")
    print(traceback.format_exc())


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error
):
    print("\n❌ ERRORE SLASH COMMAND")
    print(error)
    print(traceback.format_exc())

    try:
        if interaction.response.is_done():
            await interaction.followup.send(
                f"Errore: {error}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Errore: {error}",
                ephemeral=True
            )
    except Exception:
        pass

# =========================
# REACTION DELETE
# =========================

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """Allow users to delete their own character sheet messages with ❌ reaction"""
    # Ignore bot reactions
    if payload.user_id == bot.user.id:
        return

    # Only handle ❌ emoji
    if str(payload.emoji) != "❌":
        return

    # Check if this message is tracked
    message_id = payload.message_id
    if message_id not in bot.message_owners:
        return

    channel = bot.get_channel(payload.channel_id)
    if not channel:
        return

    # Only the owner can delete
    owner_id = bot.message_owners[message_id]
    if payload.user_id != owner_id:
        # Remove unauthorized reaction
        try:
            message = await channel.fetch_message(message_id)
            member = payload.member or await channel.guild.fetch_member(payload.user_id)
            await message.remove_reaction(payload.emoji, member)
        except Exception:
            pass
        return

    # Delete the message
    try:
        message = await channel.fetch_message(message_id)
        await message.delete()
        del bot.message_owners[message_id]
        await save_message_owners(bot.message_owners)
    except Exception as e:
        print(f"❌ Errore nel cancellare il messaggio: {e}")

# =========================
# COG LOADER
# =========================

async def load_cogs():
    for filename in os.listdir("./commands"):

        if (
            filename.endswith(".py")
            and filename != "__init__.py"
            and filename != "character_data.py"
            and filename != "message_owners_store.py"
            and filename != "gallery_store.py"
            and filename != "sheet.py"
        ):
            try:
                await bot.load_extension(
                    f"commands.{filename[:-3]}"
                )

                print(f"✅ Caricato cog: {filename}")

            except Exception as e:
                print(
                    f"❌ Errore nel caricamento di {filename}:"
                )
                traceback.print_exc()

# =========================
# READY
# =========================

_synced = False

@bot.event
async def on_ready():
    global _synced
    if not _synced:
        try:
            synced = await bot.tree.sync()
            print(f"Slash commands sincronizzati: {len(synced)}")
            for cmd in bot.tree.get_commands():
                print(f"COMANDO: {cmd.name}")
            _synced = True
        except Exception as e:
            print(f"Errore sync: {e}")

    print(f"Connesso come {bot.user}")
    
# =========================
# MAIN
# =========================

async def main():

    if not TOKEN:
        print(
            "❌ TOKEN non trovato nel file .env"
        )
        return

    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

# =========================
# START
# =========================

if __name__ == "__main__":
    asyncio.run(main())
