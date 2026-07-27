import asyncio
import json
import os

GALLERY_CONFIG_FILE = "data/gallery_config.json"


def _read_config():
    if os.path.exists(GALLERY_CONFIG_FILE):
        try:
            with open(GALLERY_CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _write_config(config):
    os.makedirs("data", exist_ok=True)
    tmp = GALLERY_CONFIG_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(config, f, indent=4)
    os.replace(tmp, GALLERY_CONFIG_FILE)


async def get_gallery_channel(guild_id) -> int | None:
    config = await asyncio.to_thread(_read_config)
    return config.get(str(guild_id))


async def set_gallery_channel(guild_id, channel_id: int):
    config = await asyncio.to_thread(_read_config)
    config[str(guild_id)] = channel_id
    await asyncio.to_thread(_write_config, config)
