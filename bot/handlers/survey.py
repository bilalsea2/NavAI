# bot/handlers/survey.py
import logging
import random
from datetime import datetime
import csv

from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command

from bot.config import (
    CATEGORIES, PROMPT_NUMBERS, ACTUAL_MODELS, ANONYMOUS_LABELS,
    MODEL_MAPPING, ANONYMOUS_TO_ACTUAL_MAPPING, RATING_QUESTIONS, PHASE1_TOTAL_CLIPS,
    PHASE1_TOTAL_SENTENCES
)
from bot.keyboards import get_rating_keyboard, get_phase2_preference_keyboard, RatingCallback, PreferenceCallback
from bot.utils.audio_manager import get_audio_path
from bot.utils.data_manager import append_phase1_data, append_phase2_data, has_completed_prompt, save_csv_to_postgres, get_completed_users

logger = logging.getLogger(__name__)
router = Router()

class SurveyStates(StatesGroup):
    PHASE1_INIT = State()
    PHASE1_SENDING_AUDIO = State()
    PHASE1_RATING_QUESTION_1 = State()
    PHASE1_RATING_QUESTION_2 = State()
    PHASE1_RATING_QUESTION_3 = State()
    PHASE1_RATING_QUESTION_4 = State()
    PHASE2_PREFERENCE = State()
    PHASE2_COMMENT = State()

# prompt_id
async def initiate_prompt(message: Message, state: FSMContext, prompt_idx: int):
    user_id = message.from_user.id
    logger.info(f"User {user_id} starting prompt {prompt_idx+1}")

    await state.set_data({
        "user_id": user_id,
        "current_category_idx": 0,
        "current_prompt_idx": prompt_idx,   # set specific prompt
        "current_model_idx": 0,
        "current_sentence_audio_order": [],
        "current_clip_ratings": [],
        "all_phase1_data": [],
        "active_prompt_idx": prompt_idx     # track which /prompt_x user chose
    })
    await state.set_state(SurveyStates.PHASE1_SENDING_AUDIO)
    await send_next_audio_clip_or_finish_phase1(message, state)

async def initiate_phase_2(message: Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"User {user_id} starting Phase 2")

    await state.set_data({
        "user_id": user_id,
        "current_category_idx": 0,
        "current_prompt_idx": 0,
        "current_model_idx": 0,
        "current_sentence_audio_order": [],
        "current_clip_ratings": [],
        "all_phase1_data": [],
        "active_prompt_idx": 0
    })
    await ask_phase2_preference(message, state)

# separate handlers for each prompts

@router.message(Command("prompt_1"))
async def start_prompt_1(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("user_id")
    if has_completed_prompt(user_id, 1):
        await message.answer("✅ Siz prompt 1-ni allaqachon tugallagansiz.")
        return
    await initiate_prompt(message, state, prompt_idx=0)


@router.message(Command("prompt_2"))
async def start_prompt_2(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("user_id")
    if has_completed_prompt(user_id, 2):
        await message.answer("✅ Siz prompt 2-ni allaqachon tugallagansiz.")
        return
    await initiate_prompt(message, state, prompt_idx=1)

@router.message(Command("prompt_3"))
async def start_prompt_3(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("user_id")
    if has_completed_prompt(user_id, 3):
        await message.answer("✅ Siz prompt 3-ni allaqachon tugallagansiz.")
        return
    await initiate_prompt(message, state, prompt_idx=2)

@router.message(Command("phase_2"))
async def start_phase_2(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("user_id")
    if user_id in get_completed_users().keys():
        await message.answer("✅ Siz so'rovnomani allaqachon tugallagansiz.")
        return
    await initiate_prompt(message, state, prompt_idx=0)

async def send_next_audio_clip_or_finish_phase1(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("user_id")

    current_category_idx = data.get("current_category_idx", 0)
    current_prompt_idx = data.get("current_prompt_idx", 0)
    current_model_idx = data.get("current_model_idx", 0)
    current_sentence_audio_order = data.get("current_sentence_audio_order", [])
    all_phase1_data = data.get("all_phase1_data", [])

    # Check if a new sentence needs to be started (i.e., all 5 models for current sentence evaluated)
    if current_model_idx == 0:
        # Check if all sentences across all categories have been covered

        if current_category_idx >= len(CATEGORIES):
            active_prompt_idx = data.get("active_prompt_idx", 0)

            logger.info(f"User {user_id} finished prompt {active_prompt_idx+1}.")
            await message.answer(
                f"Siz prompt {active_prompt_idx+1}-ni yakunladingiz ✅\n\n"
                "Keyinroq boshqa promptlarni /prompt_1 /prompt_2 /prompt_3 orqali davom ettirishingiz mumkin."
            )
            all_phase1_data = data.get("all_phase1_data", [])
            if all_phase1_data:
                print(user_id)
                append_phase1_data(user_id, all_phase1_data, prompt_id=active_prompt_idx+1)
            if all(has_completed_prompt(user_id, pid) for pid in PROMPT_NUMBERS):
                await initiate_phase_2(message, state)
            else:
                # End survey for this prompt only
                await state.clear()
            return


        current_category = CATEGORIES[current_category_idx]
        current_prompt = PROMPT_NUMBERS[current_prompt_idx]

        await message.answer(
            f"---\nEndi \"{current_category}\" kategoriyasidagi audioni baholaysiz.\n"
            f"(Prompt {current_prompt})\n---"
        )

        # Get randomized order for the 5 models for this specific sentence
        shuffled_models = list(ACTUAL_MODELS)
        random.shuffle(shuffled_models)
        current_sentence_audio_order = []
        for model in shuffled_models:
            anon_label = MODEL_MAPPING[model]
            file_path = get_audio_path(current_category, model, current_prompt)
            current_sentence_audio_order.append({
                "anonymous_label": anon_label,
                "actual_name": model,
                "file_path": file_path
            })
        
        await state.update_data(current_sentence_audio_order=current_sentence_audio_order)
        logger.info(f"User {user_id}: Starting new sentence: Category '{current_category}', Prompt '{current_prompt}'. Order: {[m['anonymous_label'] for m in current_sentence_audio_order]}")

    # Send the next audio clip from the current sentence's randomized order
    if current_model_idx < len(current_sentence_audio_order):
        clip_info = current_sentence_audio_order[current_model_idx]
        anonymous_label = clip_info["anonymous_label"]
        file_path = clip_info["file_path"]
        actual_model_name = clip_info["actual_name"]
        current_category = CATEGORIES[current_category_idx]
        current_prompt = PROMPT_NUMBERS[current_prompt_idx]

        try:
            # Use FSInputFile for local files
            audio_file = FSInputFile(file_path)
            await message.answer_audio(
                audio=audio_file,
                caption=f"Iltimos, '{anonymous_label}' audio faylini tinglang."
            )
            logger.info(f"User {user_id}: Sent audio '{anonymous_label}' ({actual_model_name}) for {current_category}/{current_prompt}.")
        except FileNotFoundError:
            logger.error(f"Audio file not found: {file_path}")
            await message.answer("Audio fayl topilmadi. Iltimos, yordam uchun bog'laning.")
            await state.clear()
            return
        except Exception as e:
            logger.error(f"Error sending audio to user {user_id}: {e}")
            await message.answer("Audio yuborishda xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko‘ring.")
            await state.clear()
            return
        
        # Prepare for the first rating question for this clip
        await state.update_data(current_clip_ratings=[], current_model_actual_name=actual_model_name)
        await state.set_state(SurveyStates.PHASE1_RATING_QUESTION_1)
        await message.answer(
            RATING_QUESTIONS[0][0],
            reply_markup=get_rating_keyboard(RATING_QUESTIONS[0][1])
        )
    else:
        # Move to next category (not next prompt!)
        current_category_idx += 1

        await state.update_data(
            current_category_idx=current_category_idx,
            current_model_idx=0,
            current_sentence_audio_order=[]
        )
        
        await state.update_data(
            current_category_idx=current_category_idx,
            current_prompt_idx=current_prompt_idx,
            current_model_idx=0, # Reset model index for new sentence
            current_sentence_audio_order=[] # Clear order for new sentence
        )
        await state.set_state(SurveyStates.PHASE1_SENDING_AUDIO)
        await send_next_audio_clip_or_finish_phase1(message, state)

@router.callback_query(RatingCallback.filter(), SurveyStates.PHASE1_RATING_QUESTION_1)
@router.callback_query(RatingCallback.filter(), SurveyStates.PHASE1_RATING_QUESTION_2)
@router.callback_query(RatingCallback.filter(), SurveyStates.PHASE1_RATING_QUESTION_3)
@router.callback_query(RatingCallback.filter(), SurveyStates.PHASE1_RATING_QUESTION_4)
async def handle_rating_callback(callback_query: CallbackQuery, callback_data: RatingCallback, state: FSMContext):
    user_id = callback_query.from_user.id
    rating_value = callback_data.value
    question_key = callback_data.question_key
    current_state = await state.get_state()
    data = await state.get_data()

    # Acknowledge callback query immediately to remove loading state
    try:
        await callback_query.answer()
        # Edit the message to remove the inline keyboard after selection
        await callback_query.message.edit_reply_markup(reply_markup=None)
        await callback_query.message.edit_text(f"{callback_query.message.text}\n\nYour rating: {rating_value}")
    except TelegramBadRequest as e:
        logger.warning(f"Could not edit message for user {user_id}: {e}")

    current_clip_ratings = data.get("current_clip_ratings", [])
    current_clip_ratings.append(rating_value)
    await state.update_data(current_clip_ratings=current_clip_ratings)
    logger.info(f"User {user_id}: Rated '{question_key}' with {rating_value}")

    # Determine the index of the current question based on the state name
    current_question_idx = int(current_state.split('_')[-1]) - 1 # Convert 'PHASE1_RATING_QUESTION_1' to index 0

    if current_question_idx + 1 < len(RATING_QUESTIONS):
        # Ask next rating question for the same clip
        next_question_idx = current_question_idx + 1
        next_question_text = RATING_QUESTIONS[next_question_idx][0]
        next_question_key = RATING_QUESTIONS[next_question_idx][1]
        await state.set_state(getattr(SurveyStates, f"PHASE1_RATING_QUESTION_{next_question_idx + 1}"))
        await callback_query.message.answer(
            next_question_text,
            reply_markup=get_rating_keyboard(next_question_key)
        )
    else:
        # All 4 questions for the current clip answered
        all_phase1_data = data.get("all_phase1_data", [])
        current_category_idx = data.get("current_category_idx")
        current_prompt_idx = data.get("current_prompt_idx")
        current_model_idx = data.get("current_model_idx")
        current_sentence_audio_order = data.get("current_sentence_audio_order")
        current_model_actual_name = data.get("current_model_actual_name")

        clip_info = current_sentence_audio_order[current_model_idx]
        anonymous_label = clip_info["anonymous_label"]

        # Prepare data for CSV
        clip_data = {
            'user_id': str(user_id),
            'timestamp_evaluation': datetime.now().isoformat(),
            'category': CATEGORIES[current_category_idx],
            'prompt_id': PROMPT_NUMBERS[current_prompt_idx],
            'model_anonymous_label': anonymous_label,
            'model_actual_name': current_model_actual_name,
            'naturalness_rating': current_clip_ratings[0],
            'clarity_rating': current_clip_ratings[1],
            'emotional_tone_rating': current_clip_ratings[2],
            'overall_preference_rating_phase1': current_clip_ratings[3]
        }
        all_phase1_data.append(clip_data)
        await state.update_data(all_phase1_data=all_phase1_data)
        logger.info(f"User {user_id}: Saved ratings for {anonymous_label} in {CATEGORIES[current_category_idx]}/{PROMPT_NUMBERS[current_prompt_idx]}. Total clips rated: {len(all_phase1_data)}/{PHASE1_TOTAL_CLIPS}")

        # Move to the next audio clip for the current sentence
        await state.update_data(current_model_idx=current_model_idx + 1)
        await state.set_state(SurveyStates.PHASE1_SENDING_AUDIO)
        
        await send_next_audio_clip_or_finish_phase1(callback_query.message, state)

async def ask_phase2_preference(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("user_id")
    logger.info(f"User {user_id}: Asking Phase 2 preference.")
    await message.answer(
        "Siz so‘rovnomaning 1-bosqichini yakunladingiz!\n\n"
        "Endi, 2-bosqichda, iltimos, qaysi audioni haqiqiy hayotda (masalan, audiokitob, call-markaz, ovozli yordamchi) eshitishni afzal ko‘rishingizni tanlang.",
        reply_markup=get_phase2_preference_keyboard()
    )
    await state.set_state(SurveyStates.PHASE2_PREFERENCE)

@router.callback_query(PreferenceCallback.filter(), SurveyStates.PHASE2_PREFERENCE)
async def handle_phase2_preference(callback_query: CallbackQuery, callback_data: PreferenceCallback, state: FSMContext):
    user_id = callback_query.from_user.id
    preferred_label = callback_data.model_label
    preferred_actual_name = ANONYMOUS_TO_ACTUAL_MAPPING.get(preferred_label, "Noma'lum")

    # Acknowledge callback query immediately
    try:
        await callback_query.answer()
        await callback_query.message.edit_reply_markup(reply_markup=None)
        await callback_query.message.edit_text(f"{callback_query.message.text}\n\nSiz tanlagan model: {preferred_label}")
    except TelegramBadRequest as e:
        logger.warning(f"Could not edit message for user {user_id}: {e}")

    await state.update_data(
        final_preferred_model_anonymous_label=preferred_label,
        final_preferred_model_actual_name=preferred_actual_name
    )
    logger.info(f"User {user_id}: Selected final preference: {preferred_label} ({preferred_actual_name})")

    await state.set_state(SurveyStates.PHASE2_COMMENT)
    await callback_query.message.answer("Rahmat! Iltimos, izohlaringizni yozing (ixtiyoriy). Izohingizni yozishingiz yoki izoh yo‘q bo‘lsa /skip buyrug‘ini yuborishingiz mumkin.")

@router.message(SurveyStates.PHASE2_COMMENT, F.text == '/skip')
@router.message(SurveyStates.PHASE2_COMMENT)
async def handle_phase2_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("user_id")
    comment = message.text if message.text != '/skip' else ""
    await state.update_data(final_comment=comment)
    logger.info(f"User {user_id}: Final comment received: '{comment}'.")

    all_phase1_data = data.get("all_phase1_data", [])
    final_preferred_model_anonymous_label = data.get("final_preferred_model_anonymous_label")
    final_preferred_model_actual_name = data.get("final_preferred_model_actual_name")

    if not all_phase1_data:
        logger.error(f"User {user_id}: No Phase 1 data found for completion.")
        await message.answer("Xatolik yuz berdi. So‘rovnoma ma'lumotlaringiz saqlanmadi. Iltimos, keyinroq qayta urinib ko‘ring.")
        await state.clear()
        return

    final_preference_data = {
        'final_preferred_model_anonymous_label': final_preferred_model_anonymous_label,
        'final_preferred_model_actual_name': final_preferred_model_actual_name,
        'final_comment': comment,
        'timestamp_survey_completion': datetime.now().isoformat()
    }

    # Save all data to CSV
    append_phase2_data(user_id, final_preference_data)
    save_csv_to_postgres()

    await message.answer(
        "So‘rovnomani yakunlaganingiz uchun rahmat! Javoblaringiz saqlandi. "
        "Siz qayta ishtirok eta olmaysiz."
    )
    logger.info(f"User {user_id} successfully completed and saved survey data.")
    await state.clear()

# Fallback for unexpected messages during survey (optional but good for robustness)
@router.message(SurveyStates.PHASE1_SENDING_AUDIO, F.text)
@router.message(SurveyStates.PHASE1_RATING_QUESTION_1, F.text)
@router.message(SurveyStates.PHASE1_RATING_QUESTION_2, F.text)
@router.message(SurveyStates.PHASE1_RATING_QUESTION_3, F.text)
@router.message(SurveyStates.PHASE1_RATING_QUESTION_4, F.text)
@router.message(SurveyStates.PHASE2_PREFERENCE, F.text)
async def handle_unexpected_text(message: Message, state: FSMContext):
    current_state = await state.get_state()
    logger.warning(f"User {message.from_user.id} sent unexpected text '{message.text}' in state {current_state}")
    if current_state and current_state.startswith("SurveyStates.PHASE1_RATING_QUESTION_"):
        await message.answer("Iltimos, baholash uchun tugmalaridan foydalaning.")
    elif current_state == "SurveyStates.PHASE2_PREFERENCE":
        await message.answer("Iltimos, afzal ko‘rgan modelni tugmalar orqali tanlang.")
    elif current_state == "SurveyStates.PHASE2_COMMENT":
        # This state also handles actual comments, so only show this if it's not a /skip
        if message.text != '/skip':
            pass # Let the handler above process the comment
        else:
            await message.answer("Iltimos, izohingizni yozing yoki /skip buyrug‘ini yuboring.")
    else:
        await message.answer("So‘rovnoma davom etmoqda. Kutilmagan ma'lumot yuborildi.")

