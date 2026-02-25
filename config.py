import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Settings:
    # Database Settings
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "estimare_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "estimare_pass")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "estimare_db")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")

    @property
    def DB_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Scraping Settings
    SCRAPE_DELAY_MIN: float = float(os.getenv("SCRAPE_DELAY_MIN", "0.25"))
    SCRAPE_DELAY_MAX: float = float(os.getenv("SCRAPE_DELAY_MAX", "0.75"))

    # Model Settings
    MODEL_SAVE_PATH: str = os.getenv("MODEL_SAVE_PATH", "xgboost_pricing_model.joblib")

settings = Settings()

"""
Instructions for updating existing files to use config.py:

1. In `database.py`:
   Replace the manual os.getenv calls and DATABASE_URL construction with:
   ```python
   from config import settings
   DATABASE_URL = settings.DB_URL
   ```

2. In `pipeline.py` / `publi24_parser.py` / `publi24_crawler.py`:
   Import the settings object to access scraping delays:
   ```python
   from config import settings
   import asyncio
   import random
   
   # Replace hardcoded delays with:
   await asyncio.sleep(random.uniform(settings.SCRAPE_DELAY_MIN, settings.SCRAPE_DELAY_MAX))
   ```

3. In `predict_price.py`:
   Import the settings object to access the model path:
   ```python
   from config import settings
   import joblib
   
   # Replace hardcoded model path with:
   model = joblib.load(settings.MODEL_SAVE_PATH)
   ```
"""
