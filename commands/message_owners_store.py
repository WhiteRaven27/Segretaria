import asyncio
import json
import os

MESSAGE_OWNERS_FILE = "data/message_owners.json"


def load_message_owners():
    """Sync — only called once at startup before the event loop is busy."""
    if os.path.exists(MESSAGE_OWNERS_FILE):
        try:
            with open(MESSAGE_OWNERS_FILE, "r") as f:
                # JSON keys are strings; convert back to int for message IDs
                return {int(k): v for k, v in json.load(f).items()}
        except Exception:
            return {}
    return {}


def _write_message_owners(data):
    os.makedirs("data", exist_ok=True)
    with open(MESSAGE_OWNERS_FILE, "w") as f:
        json.dump({str(k): v for k, v in data.items()}, f, indent=4)


async def save_message_owners(data):
    """Async — offloads disk write so it never blocks the event loop."""
    await asyncio.to_thread(_write_message_owners, data)
