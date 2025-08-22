# bot/keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

from bot.config import RATING_SCALE, ANONYMOUS_LABELS
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

class RatingCallback(CallbackData, prefix="rating"): # type: ignore
    question_key: str
    value: int

class PreferenceCallback(CallbackData, prefix="preference"): # type: ignore
    model_label: str

def get_rating_keyboard(question_key: str) -> InlineKeyboardMarkup:
    buttons = []
    for value in RATING_SCALE:
        buttons.append(InlineKeyboardButton(
            text=str(value),
            callback_data=RatingCallback(question_key=question_key, value=value).pack()
        ))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])

def get_phase2_preference_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for label in ANONYMOUS_LABELS:
        buttons.append(InlineKeyboardButton(
            text=label,
            callback_data=PreferenceCallback(model_label=label).pack()
        ))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])