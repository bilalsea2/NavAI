# bot/handlers/admin.py
import logging
import pandas as pd
import os
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command

from bot.config import ADMIN_IDS, PHASE1_RESULTS_CSV, PHASE2_RESULTS_CSV, ANONYMOUS_LABELS
from bot.utils.data_manager import get_phase1_results, get_phase2_results

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("admin_prompt_results"), F.from_user.id.in_(ADMIN_IDS))
async def admin_prompt_results_command(message: Message):
    try:
        args = message.text.strip().split()
        if len(args) < 2:
            await message.answer("Usage: /admin_prompt_results <prompt_number>")
            return
        prompt_id = int(args[1])

        df_phase1 = get_phase1_results()
        if df_phase1.empty:
            await message.answer("No Phase 1 results available.")
            return

        df_prompt = df_phase1[df_phase1['prompt_id'] == prompt_id]

        if df_prompt.empty:
            await message.answer(f"No results found for prompt {prompt_id}.")
            return

        avg_ratings = df_prompt.groupby('model_anonymous_label')['overall_preference_rating_phase1'].mean().sort_values(ascending=False)

        summary_text = f"📊 **Prompt {prompt_id} Results** 📊\n\n"
        for label, avg_score in avg_ratings.items():
            summary_text += f"`{label}`: {avg_score:.2f}\n"

        await message.answer(summary_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error generating prompt results: {e}", exc_info=True)
        await message.answer("An error occurred while fetching prompt results.")


@router.message(Command("admin_results_summary"), F.from_user.id.in_(ADMIN_IDS))
async def admin_results_summary_command(message: Message):
    user_id = message.from_user.id
    logger.info(f"Admin {user_id} requested results summary.")

    try:
        df_phase1 = get_phase1_results()
        df_phase2 = get_phase2_results()

        total_participants = df_phase1['user_id'].nunique() if not df_phase1.empty else 0
        total_phase2_completions = df_phase2['user_id'].nunique() if not df_phase2.empty else 0

        summary_text = f"📊 **Survey Results Summary** 📊\n\n"
        summary_text += f"*Total Participants (Phase 1):* `{total_participants}`\n"
        summary_text += f"*Total Phase 2 Completions:* `{total_phase2_completions}`\n\n"

        # Model Ranking by Average Overall Preference (Phase 1)
        if not df_phase1.empty and 'overall_preference_rating_phase1' in df_phase1.columns:
            df_phase1_ratings = df_phase1[df_phase1['overall_preference_rating_phase1'].notna() & (df_phase1['overall_preference_rating_phase1'] != '')].copy()
            df_phase1_ratings['overall_preference_rating_phase1'] = pd.to_numeric(df_phase1_ratings['overall_preference_rating_phase1'])
            avg_ratings = df_phase1_ratings.groupby('model_anonymous_label')['overall_preference_rating_phase1'].mean().sort_values(ascending=False)
            summary_text += "*Model Ranking by Average Overall Preference (Phase 1):*\n"
            for label, avg_score in avg_ratings.items():
                summary_text += f"  `{label}`: {avg_score:.2f}\n"
            summary_text += "\n"
        else:
            summary_text += "*No Phase 1 ratings available yet.*\n\n"

        # Model Ranking by Total Preferred Count (Phase 2)
        if not df_phase2.empty and 'final_preferred_model_anonymous_label' in df_phase2.columns:
            preferred_counts = df_phase2['final_preferred_model_anonymous_label'].value_counts()
            summary_text += "*Model Ranking by Total Preferred Count (Phase 2):*\n"
            for label, count in preferred_counts.items():
                percent = count / total_phase2_completions if total_phase2_completions else 0
                summary_text += f"  `{label}`: {count} votes ({percent:.1%})\n"
            summary_text += "\n"
        else:
            summary_text += "*No Phase 2 preference data available yet.*\n\n"

        await message.answer(summary_text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error generating summary for admin {user_id}: {e}", exc_info=True)
        await message.answer("An error occurred while generating the summary.")

@router.message(Command("admin_export_csv"), F.from_user.id.in_(ADMIN_IDS))
async def admin_export_csv_command(message: Message):
    user_id = message.from_user.id
    logger.info(f"Admin {user_id} requested CSV export.")

    try:
        files_to_send = []
        if os.path.exists(PHASE1_RESULTS_CSV) and os.path.getsize(PHASE1_RESULTS_CSV) > 0:
            files_to_send.append((PHASE1_RESULTS_CSV, "phase1_results.csv"))
        if os.path.exists(PHASE2_RESULTS_CSV) and os.path.getsize(PHASE2_RESULTS_CSV) > 0:
            files_to_send.append((PHASE2_RESULTS_CSV, "phase2_results.csv"))

        if not files_to_send:
            await message.answer("No survey results CSV files are available yet.")
            return

        for file_path, filename in files_to_send:
            document = FSInputFile(file_path, filename=filename)
            await message.answer_document(document)
            logger.info(f"Admin {user_id} successfully exported {filename}.")
    except Exception as e:
        logger.error(f"Error exporting CSV for admin {user_id}: {e}", exc_info=True)
        await message.answer("An error occurred while exporting the CSV file.")

@router.message(Command("admin_test"), F.from_user.id.in_(ADMIN_IDS))
async def admin_test(message: Message):
    await message.answer("Admin command received!")