# bot/utils/auido_manager.py
import os
import logging

from bot.config import AUDIO_DIR

logger = logging.getLogger(__name__)

def get_audio_path(category: str, model_name: str, prompt_number: int) -> str:
    """Constructs the full path to an audio file."""
    file_name = f"sample_{prompt_number}_female.wav"
    path = os.path.join(AUDIO_DIR, category, model_name, file_name)
    return path