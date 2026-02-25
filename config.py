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

    # Crawler Settings
    CRAWLER_BASE_URL: str = os.getenv("CRAWLER_BASE_URL", "https://www.publi24.ro/anunturi/imobiliare/de-vanzare/apartamente/bucuresti/")
    CRAWLER_DOMAIN: str = os.getenv("CRAWLER_DOMAIN", "https://www.publi24.ro")
    USER_AGENT: str = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    REQUEST_TIMEOUT: float = float(os.getenv("REQUEST_TIMEOUT", "15.0"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    CONCURRENCY_LIMIT: int = int(os.getenv("CONCURRENCY_LIMIT", "5"))
    MAX_PAGES_TO_CRAWL: int = int(os.getenv("MAX_PAGES_TO_CRAWL", "200"))
    OUTPUT_FILE: str = os.getenv("OUTPUT_FILE", "listing_urls.txt")

    # Model Settings
    MODEL_SAVE_PATH: str = os.getenv("MODEL_SAVE_PATH", "xgboost_pricing_model.joblib")

    # Parser Settings
    PARSER_DELAY: float = float(os.getenv("PARSER_DELAY", "0"))
    PARSER_REQUEST_TIMEOUT: float = float(os.getenv("PARSER_REQUEST_TIMEOUT", "3.0"))
    PARSER_DEBUG_FILE: str = os.getenv("PARSER_DEBUG_FILE", "debug_publi24.html")

    # Pipeline Settings
    GEOCODER_USER_AGENT: str = os.getenv("GEOCODER_USER_AGENT", "proptech_mvp_romania")
    GEOCODER_DELAY: float = float(os.getenv("GEOCODER_DELAY", "0.25"))
    PIPELINE_DELAY: float = float(os.getenv("PIPELINE_DELAY", "0.25"))
    PIPELINE_INPUT_FILE: str = os.getenv("PIPELINE_INPUT_FILE", "listing_urls.txt")

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
   Import the settings object to access scraping delays and crawler settings:
   ```python
   from config import settings
   import asyncio
   import random
   
   # Replace hardcoded delays with:
   await asyncio.sleep(random.uniform(settings.SCRAPE_DELAY_MIN, settings.SCRAPE_DELAY_MAX))
   
   # Replace hardcoded crawler settings with:
   base_url = settings.CRAWLER_BASE_URL
   user_agent = settings.USER_AGENT
   timeout = settings.REQUEST_TIMEOUT
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
