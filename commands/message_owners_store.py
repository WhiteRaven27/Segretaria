# Compatibility wrapper for legacy imports.
# Import is done lazily so this module doesn't crash during package setup.

__all__ = ["load_message_owners", "save_message_owners", "delete_message_owner"]


def load_message_owners():
    from .character_data import load_message_owners as _load_message_owners

    return _load_message_owners()


def save_message_owners(data):
    from .character_data import save_message_owners as _save_message_owners

    return _save_message_owners(data)


def delete_message_owner(message_id: int):
    from .character_data import delete_message_owner as _delete_message_owner

    return _delete_message_owner(message_id)
