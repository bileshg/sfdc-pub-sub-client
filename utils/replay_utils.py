import os
import logging

logger = logging.getLogger(__name__)


def save_replay_id(filepath: str, replay_id: bytes):
    """
    Save the replay ID to a file.
    """
    with open(filepath, "wb") as f:
        f.write(replay_id)


def load_replay_id(filepath: str) -> bytes:
    """
    Load the replay ID from a file.
    """
    if not os.path.exists(filepath):
        return b""

    with open(filepath, "rb") as f:
        return f.read()
