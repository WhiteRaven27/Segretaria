import os
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file (if it exists)
load_dotenv()

TOKEN = os.getenv("TOKEN")

# Make sure data directory exists
if not os.path.exists("data"):
    os.makedirs("data")

if not os.path.exists("data/characters.json"):
    import json
    with open("data/characters.json", "w") as f:
        json.dump({}, f)

import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# CARICAMENTO COGS
# =========================

async def load_cogs():
    """Carica tutti i cog dalla cartella commands"""
    for filename in os.listdir("./commands"):
        if filename.endswith(".py") and filename != "__init__.py" and filename != "character_data.py":
            try:
                await bot.load_extension(f"commands.{filename[:-3]}")
                print(f"✅ Caricato cog: {filename}")
            except Exception as e:
                print(f"❌ Errore nel caricamento di {filename}: {e}")

# =========================
# AVVIO BOT
# =========================

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands sincronizzati: {len(synced)}")
    except Exception as e:
        print(e)

    print(f"Connesso come {bot.user}")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
