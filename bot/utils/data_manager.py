import os
import csv
import pandas as pd
import logging
from datetime import datetime

from bot.config import PHASE1_RESULTS_CSV, PHASE2_RESULTS_CSV, PHASE1_HEADERS, PHASE2_HEADERS

logger = logging.getLogger(__name__)

def initialize_csv():
    """Initializes the CSV files with headers if they don't exist."""
    for csv_path, headers in [
        (PHASE1_RESULTS_CSV, PHASE1_HEADERS),
        (PHASE2_RESULTS_CSV, PHASE2_HEADERS)
    ]:
        if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            try:
                with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                logger.info(f"Initialized CSV file: {csv_path}")
            except IOError as e:
                logger.error(f"Error initializing CSV file {csv_path}: {e}")

def get_completed_users() -> set[int]:
    """Reads the Phase 2 CSV and returns a set of user_ids who have completed the survey."""
    completed_users = set()
    if not os.path.exists(PHASE2_RESULTS_CSV) or os.path.getsize(PHASE2_RESULTS_CSV) == 0:
        return completed_users

    try:
        df = pd.read_csv(PHASE2_RESULTS_CSV, usecols=['user_id', 'timestamp_survey_completion'], dtype={'user_id': str})
        completed_users = set(df[df['timestamp_survey_completion'].notna() & (df['timestamp_survey_completion'] != '')]['user_id'].astype(int).tolist())
    except pd.errors.EmptyDataError:
        logger.warning(f"CSV file {PHASE2_RESULTS_CSV} is empty or malformed.")
    except Exception as e:
        logger.error(f"Error reading completed users from Phase 2 CSV: {e}")
    return completed_users

def append_phase1_data(user_id: int, phase1_data: list[dict]):
    """Appends Phase 1 (audio ratings) data for a user to the Phase 1 CSV file."""
    if not phase1_data:
        logger.warning(f"No Phase 1 data to append for user {user_id}.")
        return

    data_to_write = [row.copy() for row in phase1_data]
    for row in data_to_write:
        row['user_id'] = str(user_id)
    try:
        with open(PHASE1_RESULTS_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=PHASE1_HEADERS)
            writer.writerows(data_to_write)
        logger.info(f"Successfully appended Phase 1 data for user {user_id}.")
    except IOError as e:
        logger.error(f"Error appending Phase 1 data for user {user_id} to CSV: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during Phase 1 CSV write for user {user_id}: {e}")

def append_phase2_data(user_id: int, final_preference_data: dict):
    """Appends Phase 2 (final preference) data for a user to the Phase 2 CSV file."""
    row = final_preference_data.copy()
    row['user_id'] = str(user_id)
    try:
        with open(PHASE2_RESULTS_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=PHASE2_HEADERS)
            writer.writerow(row)
        logger.info(f"Successfully appended Phase 2 data for user {user_id}.")
    except IOError as e:
        logger.error(f"Error appending Phase 2 data for user {user_id} to CSV: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during Phase 2 CSV write for user {user_id}: {e}")

def get_phase1_results() -> pd.DataFrame:
    """Reads the Phase 1 CSV into a pandas DataFrame for analysis."""
    if not os.path.exists(PHASE1_RESULTS_CSV) or os.path.getsize(PHASE1_RESULTS_CSV) == 0:
        return pd.DataFrame(columns=PHASE1_HEADERS)

    try:
        df = pd.read_csv(PHASE1_RESULTS_CSV, dtype={'user_id': str})
        return df
    except pd.errors.EmptyDataError:
        logger.warning(f"CSV file {PHASE1_RESULTS_CSV} is empty or malformed.")
        return pd.DataFrame(columns=PHASE1_HEADERS)
    except Exception as e:
        logger.error(f"Error reading Phase 1 results from CSV: {e}")
        return pd.DataFrame(columns=PHASE1_HEADERS)

def get_phase2_results() -> pd.DataFrame:
    """Reads the Phase 2 CSV into a pandas DataFrame for analysis."""
    if not os.path.exists(PHASE2_RESULTS_CSV) or os.path.getsize(PHASE2_RESULTS_CSV) == 0:
        return pd.DataFrame(columns=PHASE2_HEADERS)

    try:
        df = pd.read_csv(PHASE2_RESULTS_CSV, dtype={'user_id': str})
        return df
    except pd.errors.EmptyDataError:
        logger.warning(f"CSV file {PHASE2_RESULTS_CSV} is empty or malformed.")
        return pd.DataFrame(columns=PHASE2_HEADERS)
    except Exception as e:
        logger.error(f"Error reading Phase 2 results from CSV: {e}")
        return pd.DataFrame(columns=PHASE2_HEADERS)