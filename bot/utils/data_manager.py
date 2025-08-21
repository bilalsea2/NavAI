# bot/utils/data_manager.py
import os
import csv
import pandas as pd
import logging
from datetime import datetime
import psycopg2-binary
from psycopg2.extras import execute_values

from bot.config import (
    PHASE1_RESULTS_CSV, PHASE2_RESULTS_CSV,
    PHASE1_HEADERS, PHASE2_HEADERS,
    DATABASE_URL
)

logger = logging.getLogger(__name__)


# ---------------------- POSTGRES HELPERS ----------------------

def get_db_connection():
    """Returns a psycopg2 connection to Postgres."""
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def init_postgres_tables():
    """Creates tables in Postgres if they don’t exist yet."""
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS phase1_results (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            prompt_id TEXT,
            {', '.join([f"{col} TEXT" for col in PHASE1_HEADERS if col not in ['user_id','prompt_id']])}
        );
        """)
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS phase2_results (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            {', '.join([f"{col} TEXT" for col in PHASE2_HEADERS if col != 'user_id'])}
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
            cur.execute("DELETE FROM phase1_results;")
            if not df.empty:
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


# ---------------------- EXISTING FUNCTIONS ----------------------

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
        with open(PHASE1_RESULTS_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=PHASE1_HEADERS)
            writer.writerows(data_to_write)

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
        with open(PHASE2_RESULTS_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=PHASE2_HEADERS)
            writer.writerow(row)

        # Write Postgres
        with get_db_connection() as conn, conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO phase2_results ({','.join(PHASE2_HEADERS)}) VALUES %s",
                ([row[h] for h in PHASE2_HEADERS],)
            )
            conn.commit()

        logger.info(f"Successfully appended Phase2 data for user {user_id}.")
    except Exception as e:
        logger.error(f"Error appending Phase2 data for user {user_id}: {e}")
