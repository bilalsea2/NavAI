# bot/handlers/start.py
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bot.config import PROMPT_NUMBERS

from bot.utils.data_manager import get_completed_users, has_completed_prompt

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"User {user_id} started the bot.")

    completed_users = get_completed_users()
    if user_id in completed_users:
        await message.answer("✅ Siz so‘rovnomani to‘liq yakunlagansiz. Rahmat!")
        await state.clear()
        return

    welcome_message = (
        "O‘zbek TTS modellarini baholash so‘rovnomasiga xush kelibsiz!\n\n"
        "Ushbu anonim so‘rovnomada siz 5ta turli matndan nutqqa (TTS) modellarni baholashda yordam berasiz. "
        "Siz bir nechta audio fayllarni tinglaysiz va ularni turli mezonlar bo‘yicha baholaysiz. "
        "Sizning fikringiz TTS texnologiyalarini yaxshilash uchun juda muhim.\n\n"
        "So‘rovnoma ikki bosqichdan iborat:\n"
        "\t• **1-bosqich:** Siz \"News\", \"Literature\", \"Technical\" kategoriyalaridagi 15 ta turli audio faylni tinglaysiz. Har bir faylni tabiiylik, aniqlik, hissiy ohang va yoqimlilik bo‘yicha baholaysiz.\n"
        "\t• **2-bosqich:** Barcha fayllarni baholagandan so‘ng, siz umumiy afzal ko‘rgan modelni tanlaysiz va ixtiyoriy izoh qoldirishingiz mumkin.\n\n"
        "Barcha modellar anonim tarzda A, B, C, D, E ko'rinishida taqdim etiladi. "
        "Sizning javoblaringiz maxfiy saqlanadi va faqat tadqiqot maqsadlarida ishlatiladi.\n\n"
        "Boshlaymiz!"
    )
    # Build progress message
    progress_lines = []
    for prompt_id in PROMPT_NUMBERS:
        if has_completed_prompt(user_id, prompt_id):
            progress_lines.append(f"✅ Prompt {prompt_id} tugallangan")
        else:
            progress_lines.append(f"❌ Prompt {prompt_id} bajarilmagan (boshlash uchun /prompt_{prompt_id} bosing)")

    progress_text = (
        "📊 Sizning so‘rovnoma progressingiz:\n\n" +
        "\n".join(progress_lines) +
        "\n\nHar bir tugallanmagan promptni yuqoridagi buyruqlar orqali boshlashingiz mumkin."
    )

    await message.answer(welcome_message + "\n\n" + progress_text)
    await state.clear()


