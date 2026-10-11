"""Backend configuration — loads environment variables from .env."""
import os
from dotenv import load_dotenv

# Load .env from the project root (one level up from backend/).
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(_ROOT, ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "").strip()

# LLM provider — Google Gemini (used for off-dataset foods, meal parsing,
# and the optional analysis summary).
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()

# Demo account seeded by seed_demo.py (shown on the login screen).
DEMO_EMAIL = os.getenv("DEMO_EMAIL", "demo@nutriwise.app").strip()
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "nutriwise123").strip()

FOODS_CSV = os.path.join(_ROOT, "data", "nutriwise_foods.csv")
FRONTEND_DIST = os.path.join(_ROOT, "frontend", "dist")

ROOT_DIR = _ROOT


def is_configured() -> bool:
    """True when the minimum Supabase settings are present."""
    return bool(SUPABASE_URL and SUPABASE_ANON_KEY and SUPABASE_SERVICE_KEY)


def missing_keys() -> list:
    missing = []
    if not SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not SUPABASE_ANON_KEY:
        missing.append("SUPABASE_ANON_KEY")
    if not SUPABASE_SERVICE_KEY:
        missing.append("SUPABASE_SERVICE_KEY")
    return missing
