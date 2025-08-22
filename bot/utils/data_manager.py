# bot/utils/data_manager.py
import os
import csv
import pandas as pd
import logging
from datetime import datetime
import time
import psycopg2
from psycopg2.extras import execute_values
from psycopg2 import OperationalError
from dotenv import load_dotenv

from bot.config import PHASE1_RESULTS_CSV, PHASE2_RESULTS_CSV, PHASE1_HEADERS, PHASE2_HEADERS

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")


def get_db_connection(retries=5, delay=3):
    """Try to connect to Postgres with retries"""
    for i in range(retries):
        try:
            conn = psycopg2.connect(DATABASE_URL)
            return conn
        except OperationalError as e:
            if i < retries - 1:
                print(f"Postgres not ready yet, retrying in {delay}s... ({i+1}/{retries})")
                time.sleep(delay)
            else:
                raise e


def init_postgres_tables():
    """Creates tables in Postgres if they don’t exist yet."""
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS phase1_results (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            prompt_id TEXT,
            timestamp_evaluation TIMESTAMP,
            {', '.join([f"{col} TEXT" for col in PHASE1_HEADERS if col not in ['user_id','prompt_id', 'timestamp_evaluation']])}
        );
        """)
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS phase2_results (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            timestamp_survey_completion TIMESTAMP,
            {', '.join([f"{col} TEXT" for col in PHASE2_HEADERS if col not in ['user_id', 'timestamp_survey_completion']])}
        );
        """)
        conn.commit()


def sync_csv_with_postgres():
    """
    At startup: Load data from Postgres into CSVs.
    Ensures persistence between Railway restarts.
    """
    with get_db_connection() as conn, conn.cursor() as cur:
        # Phase1
        cur.execute("SELECT {cols} FROM phase1_results".format(cols=",".join(PHASE1_HEADERS)))
        rows = cur.fetchall()
        if rows:
            os.makedirs(os.path.dirname(PHASE1_RESULTS_CSV), exist_ok=True)
            with open(PHASE1_RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(PHASE1_HEADERS)
                writer.writerows(rows)
            logger.info(f"Synced {len(rows)} Phase1 rows from Postgres → CSV.")

        # Phase2
        cur.execute("SELECT {cols} FROM phase2_results".format(cols=",".join(PHASE2_HEADERS)))
        rows = cur.fetchall()
        if rows:
            os.makedirs(os.path.dirname(PHASE2_RESULTS_CSV), exist_ok=True)
            with open(PHASE2_RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(PHASE2_HEADERS)
                writer.writerows(rows)
            logger.info(f"Synced {len(rows)} Phase2 rows from Postgres → CSV.")



def save_csv_to_postgres():
    """
    Pushes current CSV contents → Postgres (overwrite mode).
    This ensures DB always matches CSV without duplicates.
    """
    with get_db_connection() as conn, conn.cursor() as cur:
        # Phase1
        if os.path.exists(PHASE1_RESULTS_CSV):
            df = pd.read_csv(PHASE1_RESULTS_CSV, dtype=str)
            if not df.empty:
                cur.execute("DELETE FROM phase1_results;")
                execute_values(
                    cur,
                    f"INSERT INTO phase1_results ({','.join(PHASE1_HEADERS)}) VALUES %s",
                    df[PHASE1_HEADERS].values.tolist()
                )
                logger.info(f"Saved {len(df)} Phase1 rows → Postgres.")

        # Phase2
        if os.path.exists(PHASE2_RESULTS_CSV):
            df = pd.read_csv(PHASE2_RESULTS_CSV, dtype=str)
            cur.execute("DELETE FROM phase2_results;")
            if not df.empty:
                execute_values(
                    cur,
                    f"INSERT INTO phase2_results ({','.join(PHASE2_HEADERS)}) VALUES %s",
                    df[PHASE2_HEADERS].values.tolist()
                )
                logger.info(f"Saved {len(df)} Phase2 rows → Postgres.")

        conn.commit()


def has_completed_prompt(user_id: int, prompt_id: int) -> bool:
    """
    Check if a user already completed ratings for a given category & prompt_id.
    Uses pandas for consistency with get_completed_users.
    """
    if not os.path.exists(PHASE1_RESULTS_CSV) or os.path.getsize(PHASE1_RESULTS_CSV) == 0:
        return False

    try:
        df = pd.read_csv(PHASE1_RESULTS_CSV, dtype=str)

        # Check required columns exist
        if not {'user_id', 'prompt_id'}.issubset(df.columns):
            logger.warning(f"CSV {PHASE1_RESULTS_CSV} missing required headers.")
            return False

        match = df[(df['user_id'] == str(user_id)) & (df['prompt_id'] == str(prompt_id))]
        if not match.empty:
            print(f"User {user_id} has completed prompt {prompt_id}.")
            return True

    except pd.errors.EmptyDataError:
        logger.warning(f"CSV file {PHASE1_RESULTS_CSV} is empty or malformed.")
    except Exception as e:
        logger.error(f"Error checking completion for user {user_id}, prompt {prompt_id}: {e}")

    return False

def has_completed_phase2(user_id: int) -> bool:
    """
    Check if a user has completed Phase 2 of the survey.
    """
    if not os.path.exists(PHASE2_RESULTS_CSV) or os.path.getsize(PHASE2_RESULTS_CSV) == 0:
        return False

    try:
        df = pd.read_csv(PHASE2_RESULTS_CSV, dtype=str)

        # Check required columns exist
        if not {'user_id'}.issubset(df.columns):
            logger.warning(f"CSV {PHASE2_RESULTS_CSV} missing required headers.")
            return False

        match = df[df['user_id'] == str(user_id)]
        if not match.empty:
            print(f"User {user_id} has completed Phase 2.")
            return True

def get_completed_users() -> set[int]:
    """Reads the Phase 2 CSV and returns a set of user_ids who have completed the survey."""
    completed_users = set()
    if not os.path.exists(PHASE2_RESULTS_CSV) or os.path.getsize(PHASE2_RESULTS_CSV) == 0:
        return completed_users

    try:
        df = pd.read_csv(PHASE2_RESULTS_CSV, usecols=['user_id', 'timestamp_survey_completion'], dtype={'user_id': str})
        completed_users = set(df.loc[df['timestamp_survey_completion'].notna(), 'user_id'].astype(str))
    except pd.errors.EmptyDataError:
        logger.warning(f"CSV file {PHASE2_RESULTS_CSV} is empty or malformed.")
    except Exception as e:
        logger.error(f"Error reading completed users from Phase 2 CSV: {e}")
    return completed_users

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


def append_phase1_data(user_id: int, phase1_data: list[dict], prompt_id: int = None):
    """Appends Phase 1 (audio ratings) data for a user to CSV & Postgres."""
    if not phase1_data:
        logger.warning(f"No Phase 1 data to append for user {user_id}.")
        return

    data_to_write = [row.copy() for row in phase1_data]
    for row in data_to_write:
        row['user_id'] = str(user_id)
        if prompt_id is not None:
            row['prompt_id'] = prompt_id

    try:
        # Write CSV
        file_exists = os.path.exists(PHASE1_RESULTS_CSV) and os.path.getsize(PHASE1_RESULTS_CSV) > 0
        with open(PHASE1_RESULTS_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=PHASE1_HEADERS)
            if not file_exists:
                writer.writeheader()

            # Ensure data_to_write is a list of dicts
            if isinstance(data_to_write, dict):
                writer.writerow(data_to_write)  # single dict
            elif all(isinstance(row, dict) for row in data_to_write):
                writer.writerows(data_to_write)  # list of dicts
            else:
                # Convert from tuple/list → dict
                converted = [dict(zip(PHASE1_HEADERS, row)) for row in data_to_write]
                writer.writerows(converted)


        # Write Postgres
        with get_db_connection() as conn, conn.cursor() as cur:
            execute_values(
                cur,
                f"INSERT INTO phase1_results ({','.join(PHASE1_HEADERS)}) VALUES %s",
                [[row[h] for h in PHASE1_HEADERS] for row in data_to_write]
            )
            conn.commit()

        logger.info(f"Successfully appended Phase1 data for user {user_id}, prompt {prompt_id}.")
    except Exception as e:
        logger.error(f"Error appending Phase1 data for user {user_id}: {e}")


def append_phase2_data(user_id: int, final_preference_data: dict):
    """Appends Phase 2 (final preference) data for a user to CSV & Postgres."""
    row = final_preference_data.copy()
    row['user_id'] = str(user_id)

    try:
        # Write CSV
        file_exists = os.path.exists(PHASE2_RESULTS_CSV) and os.path.getsize(PHASE2_RESULTS_CSV) > 0
        with open(PHASE2_RESULTS_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=PHASE2_HEADERS)
            if not file_exists:
                writer.writeheader()
            
            if isinstance(row, dict):
                writer.writerow(row)  # already good
            else:
                # Convert tuple/list → dict
                writer.writerow(dict(zip(PHASE2_HEADERS, row)))
        

        # Write Postgres
        with get_db_connection() as conn, conn.cursor() as cur:
            execute_values(
                cur,
                f"INSERT INTO phase2_results ({','.join(PHASE2_HEADERS)}) VALUES %s",
                [[row[h] for h in PHASE2_HEADERS]]
            )
            conn.commit()

        logger.info(f"Successfully appended Phase2 data for user {user_id}.")
    except Exception as e:
        logger.error(f"Error appending Phase2 data for user {user_id}: {e}")


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

