import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import setup_routers
from bot.utils.data_manager import initialize_csv, append_phase1_data, append_phase2_data, has_completed_prompt, init_postgres_tables, sync_csv_with_postgres
from aiogram.types import BotCommand

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_activity.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def set_commands(bot):
    commands = [
        BotCommand(command="start", description="Start the survey / Show progress"),
        BotCommand(command="prompt_1", description="Start the first batch of questions"),
        BotCommand(command="prompt_2", description="Start the second batch of questions"),
        BotCommand(command="prompt_3", description="Start the third batch of questions"),
        BotCommand(command="phase_2", description="Go to Phase 2 (final preference)"),
        BotCommand(command="help", description="Show help"),
    ]
    await bot.set_my_commands(commands)

async def main():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not found in .env file.")
        exit(1)

    # Initialize bot and dispatcher
    bot = Bot(token=bot_token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    init_postgres_tables() # Initialize Postgres tables
    sync_csv_with_postgres() # Load persisted Postgres → CSV
    initialize_csv() # Initialize in-memory CSV

    # Register routers
    setup_routers(dp)

    logger.info("Bot started polling...")
    await set_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by KeyboardInterrupt.")
    except Exception as e:
        logger.exception(f"An error occurred: {e}")