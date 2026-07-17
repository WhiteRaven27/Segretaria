import os
import json
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
# DATA FILES
# =========================

os.makedirs("data", exist_ok=True)

if not os.path.exists("data/characters.json"):
    with open("data/characters.json", "w", encoding="utf-8") as f:
        json.dump({}, f)

from commands.message_owners_store import load_message_owners, save_message_owners

# =========================
# BOT
# =========================

intents = discord.Intents.default()
intents.message_content = True

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
async def on_reaction_add(reaction, user):
    """Allow users to delete their own character sheet messages with ❌ reaction"""
    # Ignore bot reactions
    if user.bot:
        return
    
    # Only handle ❌ emoji
    if str(reaction.emoji) != "❌":
        return
    
    # Check if this message is tracked
    message_id = reaction.message.id
    if message_id not in bot.message_owners:
        return
    
    # Only the owner can delete
    owner_id = bot.message_owners[message_id]
    if user.id != owner_id:
        # Remove unauthorized reaction
        try:
            await reaction.remove(user)
        except:
            pass
        return
    
    # Delete the message
    try:
        await reaction.message.delete()
        del bot.message_owners[message_id]
        save_message_owners(bot.message_owners)
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

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands sincronizzati: {len(synced)}")

        # 👇 AGGIUNGI QUESTO
        for cmd in bot.tree.get_commands():
            print(f"COMANDO: {cmd.name}")

    except Exception as e:
        print(e)

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
