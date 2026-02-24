import time
import random
import logging
import urllib.parse
from typing import Set
import httpx
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Publi24Crawler")

class Publi24Crawler:
    """
    Crawler to extract real estate listing URLs from Publi24 search results.
    """
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.domain = "https://www.publi24.ro"
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        self.extracted_urls: Set[str] = set()

    def _sleep_politely(self, min_seconds: float = 2.0, max_seconds: float = 4.0):
        """Sleeps for a random duration to avoid triggering anti-bot protections."""
        delay = random.uniform(min_seconds, max_seconds)
        logger.info(f"Sleeping for {delay:.2f} seconds...")
        time.sleep(delay)

    def fetch_search_page(self, page_number: int) -> str | None:
        """
        Fetches the HTML of a search results page.
        """
        self._sleep_politely()
        
        # Construct URL with pagination parameter
        # Example: ?pag=1
        params = {"pag": page_number}
        headers = {"User-Agent": self.user_agent}
        
        target_url = f"{self.base_url}?{urllib.parse.urlencode(params)}"
        logger.info(f"Fetching search page: {target_url}")
        
        try:
            response = httpx.get(target_url, headers=headers, timeout=15.0)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as e:
            logger.error(f"HTTP error occurred fetching page {page_number}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching page {page_number}: {e}")
            return None

    def extract_urls_from_html(self, html: str) -> Set[str]:
        """
        Parses HTML and extracts valid listing URLs.
        """
        soup = BeautifulSoup(html, "html.parser")
        found_urls = set()
        
        # Find all link tags
        links = soup.find_all("a", href=True)
        
        for link in links:
            href = link["href"]
            
            # Filter logic: Publi24 listings typically contain '/anunt/' and end with '.html'
            if "/anunt/" in href and href.endswith(".html"):
                
                # Make URL absolute if it is relative
                if href.startswith("/"):
                    absolute_url = f"{self.domain}{href}"
                elif not href.startswith("http"):
                    # Handle cases where it might just be the path without leading slash
                    absolute_url = f"{self.domain}/{href}"
                else:
                    absolute_url = href
                    
                found_urls.add(absolute_url)
                
        return found_urls

    def save_urls_to_file(self, filename: str = "listing_urls.txt"):
        """Saves the accumulated URLs to a plain text file."""
        if not self.extracted_urls:
            logger.warning("No URLs to save.")
            return

        try:
            with open(filename, "w", encoding="utf-8") as f:
                for url in sorted(self.extracted_urls):
                    f.write(f"{url}\n")
            logger.info(f"Successfully saved {len(self.extracted_urls)} unique URLs to {filename}")
        except IOError as e:
            logger.error(f"Failed to write URLs to {filename}: {e}")

    def run(self, max_pages: int = 3):
        """
        Main execution loop to crawl multiple pages.
        """
        logger.info(f"Starting Publi24 crawler for {max_pages} pages. Base URL: {self.base_url}")
        
        for page in range(1, max_pages + 1):
            logger.info(f"Processing Page {page}/{max_pages}")
            
            html = self.fetch_search_page(page)
            if not html:
                logger.warning(f"Could not retrieve HTML for page {page}. Skipping to next.")
                continue
                
            urls_on_page = self.extract_urls_from_html(html)
            
            if not urls_on_page:
                logger.warning(f"No valid listing URLs found on page {page}.")
            else:
                logger.info(f"Found {len(urls_on_page)} listing URLs on page {page}.")
                self.extracted_urls.update(urls_on_page)
                
            logger.info(f"Total unique URLs collected so far: {len(self.extracted_urls)}")
            
        # Save results at the end
        self.save_urls_to_file()
        logger.info(f"Crawler finished. Extracted a total of {len(self.extracted_urls)} unique URLs.")

if __name__ == "__main__":
    # Base URL for apartments in Bucharest
    target_search_url = "https://www.publi24.ro/anunturi/imobiliare/de-vanzare/apartamente/bucuresti/"
    
    crawler = Publi24Crawler(base_url=target_search_url)
    crawler.run(max_pages=3)
