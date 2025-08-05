import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.utils.data_manager import get_completed_users
from bot.handlers.survey import initiate_survey, SurveyStates

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"User {user_id} started the bot.")

    completed_users = get_completed_users()

    if user_id in completed_users:
        await message.answer(
            "Ishtirokingiz uchun rahmat! Siz so‘rovnomani allaqachon yakunlagansiz."
        )
        await state.clear()
        logger.info(f"User {user_id} attempted to restart, but already completed.")
        return

    welcome_message = (
        "O‘zbek TTS modelini baholash so‘rovnomasiga xush kelibsiz!\n\n"
        "Ushbu anonim so‘rovnomada siz turli matndan nutqqa (TTS) modellarni baholashda yordam berasiz. "
        "Siz bir nechta audio fayllarni tinglaysiz va ularni turli mezonlar bo‘yicha baholaysiz. "
        "Sizning fikringiz TTS texnologiyalarini yaxshilash uchun juda muhim.\n\n"
        "So‘rovnoma ikki bosqichdan iborat:\n"
        "\t• **1-bosqich:** Siz 9 ta noyob gapni tinglaysiz, har bir gap uchun 5 ta audio fayl bo‘ladi. Har bir faylni tabiiylik, aniqlik, hissiy ohang va yoqimlilik bo‘yicha baholaysiz.\n"
        "\t• **2-bosqich:** Barcha fayllarni baholagandan so‘ng, siz umumiy afzal ko‘rgan modelni tanlaysiz va ixtiyoriy izoh qoldirishingiz mumkin.\n\n"
        "Barcha modellar anonim tarzda (masalan, A, B, C) taqdim etiladi. "
        "Sizning javoblaringiz maxfiy saqlanadi va faqat tadqiqot maqsadlarida ishlatiladi.\n\n"
        "Boshlaymiz!"
    )

    await message.answer(welcome_message)
    await state.set_state(SurveyStates.PHASE1_INIT)
    await initiate_survey(message, state)