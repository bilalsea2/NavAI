# Uzbek TTS models benchmarking

Telegram bot for anonymous benchmarking of Uzbek TTS models (female voices). Users rate audio clips and select their preferred model.

## Features

-   Anonymous survey: models are presented as A, B, C, etc.
-   Two-phase evaluation: rate audio clips, then select overall preference.
-   Results saved to `survey_results.csv`.

## Setup

1.  **Clone the repository**

    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

2.  **Create `.env` file**  
    Add your Telegram Bot Token and admin user IDs:

    ```
    TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN_HERE"
    ADMIN_IDS="YOUR_ADMIN_USER_ID_1,YOUR_ADMIN_USER_ID_2"
    ```

3.  **Add audio files**  
    Place your `.wav` files in `audio/<Category>/<Model Name>/sample_<Prompt Number>_female.wav`.

4.  **Install dependencies**

    ```bash
    pip install -r requirements.txt
    ```

5.  **Run the bot**

    ```bash
    python main.py
    ```

## Bot Commands

-   `/start` — Begin the survey (if not completed before)
-   `/admin_results_summary` — Show survey summary (admin only)
-   `/admin_export_csv` — Export results CSV (admin only)
-   `/admin_test` — Test admin panel (admin only)

## Data

Results are saved in `survey_results.csv` in the `data/` directory.