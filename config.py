import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

# Load .env if present
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

class Settings(BaseModel):
    creators_area_token: str = os.getenv('CREATORS_AREA_TOKEN', '').strip()
    portfolio_url: str = os.getenv('PORTFOLIO_URL', 'https://github.com/').strip()
    poll_interval_seconds: int = int(os.getenv('POLL_INTERVAL_SECONDS', '10'))
    allow_volunteer: bool = os.getenv('ALLOW_VOLUNTEER', 'true').lower() in ('true', '1', 'yes')
    min_price: float = float(os.getenv('MIN_PRICE', '0'))
    discord_webhook_url: str = os.getenv('DISCORD_WEBHOOK_URL', '').strip()
    dry_run: bool = os.getenv('DRY_RUN', 'false').lower() in ('true', '1', 'yes')
    max_offer_age_hours: int = int(os.getenv('MAX_OFFER_AGE_HOURS', '24'))
    ai_provider: str = os.getenv('AI_PROVIDER', 'none').lower().strip()
    ai_api_key: str = os.getenv('AI_API_KEY', '').strip()
    ai_model: str = os.getenv('AI_MODEL', '').strip()

settings = Settings()
