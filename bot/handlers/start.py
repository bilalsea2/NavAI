# bot/handlers/start.py
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bot.config import PROMPT_NUMBERS

from bot.utils.data_manager import has_completed_prompt, has_completed_phase2

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"User {user_id} started the bot.")

    if has_completed_phase2(user_id):
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

    if all(has_completed_prompt(user_id, pid) for pid in PROMPT_NUMBERS) and not :
        progress_text += ("\n\n🎯 Siz barcha promptlarni tugalladingiz! "
        "Endi umumiy afzal ko‘rgan modelni tanlash uchun Phase 2 ga o‘ting.\n"
        "Boshlash uchun /phase_2 ni bosing.")

    await message.answer(welcome_message + "\n\n" + progress_text)
    await state.clear()

@router.message(Command("progress"))
async def progress_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested progress.")

    if has_completed_phase2(user_id):
        await message.answer("✅ Siz so‘rovnomani to‘liq yakunlagansiz. Rahmat!")
        await state.clear()
        return

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

    if all(has_completed_prompt(user_id, pid) for pid in PROMPT_NUMBERS):
        progress_text += ("\n\n🎯 Siz barcha promptlarni tugalladingiz! "
        "Endi umumiy afzal ko‘rgan modelni tanlash uchun Phase 2 ga o‘ting.\n"
        "Boshlash uchun /phase_2 ni bosing.")

    await message.answer(progress_text)
    await state.clear()


