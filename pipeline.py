import asyncio
import logging
import time
import re
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from geoalchemy2.elements import WKTElement
from geopy.geocoders import Nominatim

from database import AsyncSessionLocal, engine, init_db
from models import Base, Property, Listing
from publi24_parser import Publi24ListingParser
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Pipeline")

def extract_floor(features: dict) -> int | None:
    """
    Extracts and converts the floor value from the features dictionary.
    """
    floor_str = features.get("Etaj")
    if not floor_str:
        return None
    
    floor_str = floor_str.lower().strip()
    if "parter" in floor_str:
        return 0
    if "demisol" in floor_str:
        return -1
    if "mansarda" in floor_str:
        return 99 # Or some other convention for mansard
    
    # Try to extract integer
    match = re.search(r'-?\d+', floor_str)
    if match:
        return int(match.group())
    return None

def extract_total_rooms(features: dict, title: str, description: str) -> int | None:
    """
    Extracts the total number of rooms from features, title, or description.
    """
    # 1. Try from features
    rooms_str = features.get("Numar camere")
    if rooms_str:
        match = re.search(r'\d+', str(rooms_str))
        if match:
            return int(match.group())
            
    # 2. Try from title
    if title:
        # Look for patterns like "3 camere", "2 cam", "apartament 4 camere"
        match = re.search(r'(\d+)\s*camere?', title, re.IGNORECASE)
        if match:
            return int(match.group(1))
            
    # 3. Try from description
    if description:
        match = re.search(r'(\d+)\s*camere?', description, re.IGNORECASE)
        if match:
            return int(match.group(1))
            
    return None

async def process_urls(urls_file: str):
    """
    Reads URLs from a file and processes them, saving data to the database.
    """
    try:
        with open(urls_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logger.error(f"File not found: {urls_file}")
        return

    total_urls = len(urls)
    logger.info(f"Found {total_urls} URLs to process.")

    parser = Publi24ListingParser()
    geolocator = Nominatim(user_agent=settings.GEOCODER_USER_AGENT)

    async with AsyncSessionLocal() as session:
        for i, url in enumerate(urls, 1):
            logger.info(f"Processing {i}/{total_urls}: {url}")

            try:
                # 4. Duplicate Handling: Check if URL already exists
                stmt = select(Listing).where(Listing.listing_url == url)
                result = await session.execute(stmt)
                existing_listing = result.scalars().first()

                if existing_listing:
                    logger.info(f"Skipping {url} - already exists in database.")
                    continue

                # 5. Parse Data
                html_content = parser.fetch_html(url)
                if not html_content:
                    logger.warning(f"Failed to fetch HTML for {url}. Skipping.")
                    continue

                json_data = parser.extract_json_ld(html_content)
                if not json_data:
                    logger.warning(f"Failed to extract JSON-LD for {url}. Skipping.")
                    continue

                parsed_data = parser.parse_listing(json_data)

                # 8. Database Mapping
                # Create Property object
                # Note: features is not in the Property model, so we skip it or we would need to add it to the model.
                # The instructions say "features stored as JSONB if applicable", but the model doesn't have it.
                # I will map what is available in the model.
                
                # Extract floor and total_rooms from features if possible, or leave None
                features = parsed_data.get("features", {})
                title = parsed_data.get("title", "")
                description = parsed_data.get("description", "")
                
                floor = extract_floor(features)
                total_rooms = extract_total_rooms(features, title, description)
                
                property_type = "unknown" # Default type, as it's required (nullable=False)
                # Try to infer type from URL or title
                title_lower = parsed_data.get("title", "").lower()
                url_lower = url.lower()
                if "apartament" in title_lower or "apartament" in url_lower:
                    property_type = "apartment"
                elif "casa" in title_lower or "casa" in url_lower or "vila" in title_lower:
                    property_type = "house"
                elif "teren" in title_lower or "teren" in url_lower:
                    property_type = "land"

                # Geocoding
                location_wkt = None
                location_region = parsed_data.get("location_region")
                location_locality = parsed_data.get("location_locality")
                
                if location_locality and location_region:
                    search_query = f"{location_locality}, {location_region}, Romania"
                    try:
                        logger.info(f"Geocoding: {search_query}")
                        # Run synchronous geocode in a thread to avoid blocking the event loop
                        location_data = await asyncio.to_thread(geolocator.geocode, search_query)
                        if location_data:
                            # PostGIS expects POINT(longitude latitude)
                            location_wkt = WKTElement(f'POINT({location_data.longitude} {location_data.latitude})', srid=4326)
                            logger.info(f"Geocoded successfully: {location_data.latitude}, {location_data.longitude}")
                        else:
                            logger.warning(f"Geocoding failed for: {search_query}")
                    except Exception as e:
                        logger.error(f"Geocoding error for {search_query}: {e}")
                    
                    # Strict delay for Nominatim
                    await asyncio.sleep(settings.GEOCODER_DELAY)

                new_property = Property(
                    type=property_type,
                    build_year=parsed_data.get("year_built"),
                    usable_area_sqm=parsed_data.get("usable_area_sqm"),
                    floor=floor,
                    total_rooms=total_rooms,
                    location=location_wkt
                )
                
                session.add(new_property)
                await session.flush() # Flush to get the property ID

                # Create Listing object
                price = parsed_data.get("price")
                if price is None:
                    price = 0.0 # asking_price_eur is nullable=False, so we need a default if missing
                    
                new_listing = Listing(
                    property_id=new_property.id,
                    asking_price_eur=price,
                    listing_url=url,
                    description_text=parsed_data.get("description"),
                    status="active"
                )
                
                session.add(new_listing)
                await session.commit()
                
                logger.info(f"Processing {i}/{total_urls}: {url}... Saved to DB.")

            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Database error processing {url}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error processing {url}: {e}")
            
            # 6. Delay: Add a realistic delay (e.g., 3-5 seconds) between each request to maintain politeness.
            # Note: fetch_html already has a delay, but we can add a small one here too or rely on the one in fetch_html.
            # The instructions say "Add a realistic delay (e.g., 3-5 seconds) between each request".
            # Since fetch_html has time.sleep(), we are already delaying. I'll add a small async sleep here just in case.
            await asyncio.sleep(settings.PIPELINE_DELAY)

async def main():
    # Initialize database tables (optional, usually done via migrations)
    # await init_db(Base.metadata)
    
    urls_file = settings.PIPELINE_INPUT_FILE
    await process_urls(urls_file)

if __name__ == "__main__":
    asyncio.run(main())
