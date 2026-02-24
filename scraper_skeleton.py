import asyncio
import random
import logging
import re
from typing import Optional, Dict, Any

# Configure clear logging to track the scraper's execution
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ScraperBase")

class BaseScraper:
    """
    Base class structure for real estate web scrapers.
    Implements rate limiting, common cleanups, and a framework to prevent blocks.
    """
    def __init__(self, base_url: str, min_delay: float = 2.0, max_delay: float = 6.0):
        self.base_url = base_url
        self.min_delay = min_delay
        self.max_delay = max_delay

    async def _random_delay(self):
        """
        Pauses execution for a random duration between min_delay and max_delay seconds
        to mimic human browsing behavior and avoid IP bans or rate limiting blocks.
        """
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.debug(f"Sleeping for {delay:.2f} seconds...")
        await asyncio.sleep(delay)

    async def fetch_page(self, url: str) -> Optional[str]:
        """
        Fetches the HTML content of a page.
        This is a placeholder and MUST be implemented by subclasses
        using asynchronous tools like Playwright or httpx.
        """
        raise NotImplementedError("Subclasses must implement fetch_page method.")

    def parse_listing(self, html_content: str, url: str) -> Dict[str, Any]:
        """
        Placeholder function to parse a generic listing page.
        Extracts relevant features like price, area, description, etc.
        """
        # Example logic to be replaced by actual BeautifulSoup or Playwright parsing
        logger.info(f"Parsing raw data for {url}")
        
        parsed_data = {
            "title": "Placeholder Real Estate Property",
            "price_raw": "100.000 EUR",
            "usable_area_raw": "50 sqm",
            "description": "This is a placeholder description text scraped from HTML.",
            "url": url
        }
        return parsed_data

    @staticmethod
    def clean_price(price_str: str) -> Optional[float]:
        """
        Cleans a price string and converts it to a float.
        Target: handles variations like "100.000 EUR", "100,000", "€100.000" -> 100000.0
        """
        if not price_str:
            return None
        
        try:
            # 1. Standardize string: uppercase, remove symbols, strip whitespaces
            cleaned_str = price_str.upper().replace('EUR', '').replace('€', '').strip()
            
            # 2. Handle Romanian formatting (dots as thousand separators)
            # E.g., "100.000,50" or "100.000"
            if ',' in cleaned_str and '.' in cleaned_str:
                # Format: 100.000,50 -> 100000.50
                cleaned_str = cleaned_str.replace('.', '').replace(',', '.')
            elif ',' in cleaned_str:
                # Format: 100000,50 -> 100000.50
                cleaned_str = cleaned_str.replace(',', '.')
            else:
                # Format: 100.000 -> 100000 or 100000 -> 100000
                cleaned_str = cleaned_str.replace('.', '')
                
            # 3. Extract the numeric part (including decimal points)
            match = re.search(r'[\d\.]+', cleaned_str)
            if match:
                return float(match.group())
            return None
        
        except Exception as e:
            logger.error(f"Error cleaning price '{price_str}': {e}")
            return None

    async def run_scraper(self, urls: list[str]) -> list[Dict[str, Any]]:
        """
        Main execution loop for the scraper, demonstrating error handling and delays.
        """
        results = []
        for url in urls:
            try:
                logger.info(f"Starting to process: {url}")
                
                # Apply random delay before request
                await self._random_delay()
                
                # Fetch page content
                try:
                    html_content = await asyncio.wait_for(self.fetch_page(url), timeout=30.0)
                except asyncio.TimeoutError:
                    logger.error(f"Timeout while fetching {url}. Skipping.")
                    continue
                
                if not html_content:
                    logger.warning(f"Failed to retrieve valid content for {url}. Skipping.")
                    continue
                
                # Parse listing properties
                raw_data = self.parse_listing(html_content, url)
                
                # Clean numerical fields
                price = self.clean_price(raw_data.get("price_raw"))
                raw_data["asking_price_eur"] = price
                
                results.append(raw_data)
                logger.info(f"Successfully processed and appended results for: {url}")
                
            except Exception as e:
                logger.error(f"Critical error while processing {url}: {e}", exc_info=True)
                
        return results

# Basic testing usage wrapper snippet
# if __name__ == "__main__":
#     class DummyScraper(BaseScraper):
#         async def fetch_page(self, url: str) -> Optional[str]:
#             return "<html>Dummy Content</html>"
#
#     async def main():
#         scraper = DummyScraper(base_url="https://example.com")
#         await scraper.run_scraper(["https://example.com/property/1"])
#         
#     asyncio.run(main())
