import os
from dotenv import load_dotenv
load_dotenv()
# Admin User IDs (comma-separated in .env)
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(',') if x.strip()]
print(f"Admin IDs: {ADMIN_IDS}")

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(BASE_DIR, 'audio')
DATA_DIR = os.path.join(BASE_DIR, 'data')
PHASE1_RESULTS_CSV = os.path.join(DATA_DIR, 'phase1_results.csv')  # Changed filename
PHASE2_RESULTS_CSV = os.path.join(DATA_DIR, 'phase2_results.csv')  # Added filename

# Survey Configuration
CATEGORIES = ['News', 'Literature', 'Technical']
PROMPT_NUMBERS = [1, 2, 3]
ACTUAL_MODELS = ['NavAI', 'Yandex Speech Kit', 'UzbekVoice', 'Muxlisa', 'Aisha']
ANONYMOUS_LABELS = ['A', 'B', 'C', 'D', 'E']

MODEL_MAPPING = dict(zip(ACTUAL_MODELS, ANONYMOUS_LABELS))
ANONYMOUS_TO_ACTUAL_MAPPING = dict(zip(ANONYMOUS_LABELS, ACTUAL_MODELS))

# Rating Questions and Callback Data Prefixes
RATING_QUESTIONS = [
    ("How natural does the voice sound? (1: robotic → 5: completely human-like)", "naturalness"),
    ("How clear and understandable is the speech? (1: unclear → 5: very clear)", "clarity"),
    ("How well is the emotional tone conveyed? (1: flat/monotone → 5: expressive/engaging)", "emotional_tone"),
    ("How pleasant is the voice to listen to? (1: unpleasant → 5: very pleasant)", "overall_preference_phase1"),
]
RATING_SCALE = [1, 2, 3, 4, 5]

# Total evaluations per user in Phase 1
PHASE1_TOTAL_CLIPS = len(CATEGORIES) * len(PROMPT_NUMBERS) * len(ACTUAL_MODELS)
PHASE1_TOTAL_SENTENCES = len(CATEGORIES) * len(PROMPT_NUMBERS)

# CSV Headers for Phase 1 (audio ratings)
PHASE1_HEADERS = [
    'user_id',
    'timestamp_evaluation',
    'category',
    'prompt_id',
    'model_anonymous_label',
    'model_actual_name',
    'naturalness_rating',
    'clarity_rating',
    'emotional_tone_rating',
    'overall_preference_rating_phase1'
]

# CSV Headers for Phase 2 (final preference)
PHASE2_HEADERS = [
    'user_id',
    'final_preferred_model_anonymous_label',
    'final_preferred_model_actual_name',
    'final_comment',
    'timestamp_survey_completion'
]

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)