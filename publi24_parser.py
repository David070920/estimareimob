import json
import logging
import time
from typing import Dict, Any, List, Optional
import httpx
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Publi24ListingParser")

from config import settings

class Publi24ListingParser:
    """
    Parser for Publi24 real estate listings.
    Extracts structured data embedded as JSON-LD in the HTML source code.
    """
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    )

    def fetch_html(self, url: str) -> Optional[str]:
        """
        Fetches the HTML source of a Publi24 listing URL using httpx.
        Includes a delay to be polite to the server.
        
        Args:
            url (str): The URL of the listing to fetch.
            
        Returns:
            Optional[str]: The HTML content if successful, None otherwise.
        """
        logger.info(f"Sleeping for {settings.PARSER_DELAY} seconds before requesting: {url}")
        time.sleep(settings.PARSER_DELAY)
        
        headers = {"User-Agent": self.USER_AGENT}
        try:
            # Using httpx to synchronously get the page
            response = httpx.get(url, headers=headers, timeout=settings.PARSER_REQUEST_TIMEOUT)
            response.raise_for_status()
            logger.info(f"Successfully fetched page: {url}")
            
            # Debug: Save raw HTML to file to check for captchas or bot protections
            with open(settings.PARSER_DEBUG_FILE, "w", encoding="utf-8") as f:
                f.write(response.text)
            logger.info(f"Saved raw HTML to {settings.PARSER_DEBUG_FILE} for manual inspection.")
            
            return response.text
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred while fetching {url}: {e}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error occurred while fetching {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while fetching {url}: {e}")
            return None

    def extract_json_ld(self, html: str) -> Optional[Dict[str, Any]]:
        """
        Extracts the JSON-LD data from the HTML source.
        
        Args:
            html (str): The source HTML of the page.
            
        Returns:
            Optional[Dict[str, Any]]: The parsed JSON dictionary, or None if not found.
        """
        soup = BeautifulSoup(html, "html.parser")
        
        # Find all JSON-LD script tags
        script_tags = soup.find_all("script", type="application/ld+json")
        if not script_tags:
            logger.warning("No JSON-LD scripts found on the page.")
            return None
            
        for index, tag in enumerate(script_tags):
            if not tag.string:
                continue
                
            try:
                # Clean up string before parsing due to potential malformed JSON with newlines in strings
                clean_string = tag.string.replace('\r', '').replace('\n', '').replace('\t', '').strip()
                data = json.loads(clean_string)
                
                # Print the @type for debugging purposes
                if isinstance(data, dict):
                    logger.debug(f"Script {index}: Found JSON-LD of type: {data.get('@type')}")
                    
                    # Target Identification: We are looking for Product with offers
                    if data.get("@type") == "Product" and "offers" in data:
                        logger.info(f"Script {index}: Successfully identified target JSON-LD listing object.")
                        return data
                        
                    # Also check inside @graph for cases where multiple entities are bundled
                    if "@graph" in data:
                        for graph_item in data["@graph"]:
                            if isinstance(graph_item, dict):
                                logger.debug(f"Script {index} (@graph item): Found JSON-LD of type: {graph_item.get('@type')}")
                                if graph_item.get("@type") == "Product" and "offers" in graph_item:
                                    logger.info(f"Script {index}: Successfully identified target JSON-LD listing object within @graph.")
                                    return graph_item
                
                # Handle lists of JSON-LD objects
                elif isinstance(data, list):
                    for item_index, item in enumerate(data):
                        if isinstance(item, dict):
                            logger.debug(f"Script {index} (list item {item_index}): Found JSON-LD of type: {item.get('@type')}")
                            if item.get("@type") == "Product" and "offers" in item:
                                logger.info(f"Script {index}: Successfully identified target JSON-LD listing object from list.")
                                return item
                                
            except json.JSONDecodeError as e:
                logger.debug(f"Script {index}: JSONDecodeError parsing script tag: {e}")
                
                # Try a more aggressive cleanup if the first one failed
                try:
                    # Sometimes they have unescaped quotes or trailing commas
                    import re
                    # Remove trailing commas from objects or arrays
                    fixed_string = re.sub(r',(\s*[}\]])', r'\1', clean_string)
                    data = json.loads(fixed_string)
                    logger.debug(f"Script {index}: Recovered from JSONDecodeError with aggressive cleanup. Type: {data.get('@type') if isinstance(data, dict) else 'list'}")
                    
                    if isinstance(data, dict) and data.get("@type") == "Product" and "offers" in data:
                        logger.info(f"Script {index}: Successfully identified target JSON-LD listing object after recovery.")
                        return data
                except:
                    continue
                
        logger.warning("Could not identify the main real estate JSON-LD object containing 'offers' and '@type' Product.")
        return None

    def _flatten_features(self, additional_properties: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Helper function to flatten the list of additional properties.
        Example input: [{"name": "Numar bai", "value": "1"}, ...]
        Example output: {"Numar bai": "1", ...}
        
        Args:
            additional_properties (List[Dict[str, Any]]): List of property dictionaries.
            
        Returns:
            Dict[str, str]: Flattened dictionary of features.
        """
        features_dict = {}
        if not isinstance(additional_properties, list):
            return features_dict
            
        for prop in additional_properties:
            if isinstance(prop, dict):
                name = prop.get("name")
                value = prop.get("value")
                if name and value:
                    features_dict[str(name)] = str(value)
        return features_dict

    def _parse_numeric(self, value: Any, is_float: bool = False) -> Optional[float | int]:
        """
        Attempts to cast a value to float or integer.
        """
        if value is None:
            return None
            
        try:
            if is_float:
                return float(value)
            return int(float(value))
        except (ValueError, TypeError):
            return None

    def parse_listing(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses the specific nested fields from the JSON-LD dictionary.
        
        Args:
            json_data (Dict[str, Any]): The loaded JSON-LD data.
            
        Returns:
            Dict[str, Any]: A flat, clean dictionary ready for insertion into the database.
        """
        # Top level attributes
        title = json_data.get("name")
        description = json_data.get("description")
        url = json_data.get("url")
        
        # Images 
        images = []
        raw_images = json_data.get("image", [])
        if isinstance(raw_images, list):
            for img in raw_images:
                if isinstance(img, dict) and "contentUrl" in img:
                    images.append(img.get("contentUrl"))
                elif isinstance(img, str):
                    images.append(img)
        elif isinstance(raw_images, dict) and "contentUrl" in raw_images:
            images.append(raw_images.get("contentUrl"))
        elif isinstance(raw_images, str):
            images.append(raw_images)

        # Offers block
        offers = json_data.get("offers", {})
        if isinstance(offers, list) and len(offers) > 0:
             offers = offers[0]
             
        price = self._parse_numeric(offers.get("price"), is_float=True)
        currency = offers.get("priceCurrency")
        
        # Location 
        available_at = offers.get("availableAtOrFrom", {})
        if isinstance(available_at, list) and len(available_at) > 0:
             available_at = available_at[0]
             
        address = available_at.get("address", {})
        location_region = address.get("addressRegion")
        location_locality = address.get("addressLocality")
        
        # Item offered block
        item_offered = offers.get("itemOffered", {})
        
        # Area
        floor_size = item_offered.get("floorSize", {})
        usable_area = self._parse_numeric(floor_size.get("value"), is_float=True)
        
        # Build year
        year_built_raw = item_offered.get("yearBuilt")
        # In case yearBuilt is an object or string
        if isinstance(year_built_raw, dict) and "value" in year_built_raw:
            year_built = self._parse_numeric(year_built_raw.get("value"))
        else:
            year_built = self._parse_numeric(year_built_raw)
            
        # Features / Additional Properties
        raw_features = item_offered.get("additionalProperty", [])
        features = self._flatten_features(raw_features)

        parsed_data = {
            "title": title,
            "description": description,
            "url": url,
            "images": images,
            "price": price,
            "currency": currency,
            "location_region": location_region,
            "location_locality": location_locality,
            "usable_area_sqm": usable_area,
            "year_built": year_built,
            "features": features
        }
        
        return parsed_data

if __name__ == "__main__":
    import pprint
    
    # Example test with a hypothetical Publi24 url 
    # Use a real URL here to test the script end-to-end
    test_url = "https://www.publi24.ro/anunturi/imobiliare/de-vanzare/apartamente/apartamente-3-camere/anunt/armenasca-ultracentral-ideal-investitie/9dddh669gd227d372ed41e3fg5h42f08.html"    
    parser = Publi24ListingParser()
    
    logger.info("Starting Publi24 JSON-LD extraction test...")
    html_content = parser.fetch_html(test_url)
    
    if html_content:
        logger.info("HTML fetched successfully. Extracting JSON-LD...")
        json_data = parser.extract_json_ld(html_content)
        
        if json_data:
            logger.info("JSON-LD successfully extracted. Parsing data...")
            cleaned_listing = parser.parse_listing(json_data)
            
            print("\n" + "="*50)
            print("Extracted Structured Data:")
            print("="*50)
            pprint.pprint(cleaned_listing)
        else:
            logger.error("Could not find or extract JSON-LD.")
    else:
        logger.error("Failed to fetch HTML. Can't proceed.")
