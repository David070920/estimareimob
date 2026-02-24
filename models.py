import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship
from geoalchemy2 import Geometry

Base = declarative_base()

class Property(Base):
    """
    Property model representing a physical real estate asset.
    """
    __tablename__ = 'properties'

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String, index=True, nullable=False) # e.g., 'apartment', 'house', 'land'
    build_year = Column(Integer, nullable=True)
    usable_area_sqm = Column(Float, nullable=True)
    floor = Column(Integer, nullable=True)
    total_rooms = Column(Integer, nullable=True)
    
    # Store location as a PostGIS Geometry/Point type 
    # SRID 4326 is WGS84 - standard for GPS coordinates (latitude/longitude)
    location = Column(Geometry(geometry_type='POINT', srid=4326), nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    # Relationship to listings
    listings = relationship("Listing", back_populates="property", cascade="all, delete-orphan")

class Listing(Base):
    """
    Listing model representing an advertisement for a property.
    A single property might have multiple listings over time or across different platforms.
    """
    __tablename__ = 'listings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(Integer, ForeignKey('properties.id'), nullable=False)
    asking_price_eur = Column(Float, nullable=False)
    listing_url = Column(String, unique=True, nullable=False)
    description_text = Column(String, nullable=True)
    status = Column(String, default="active", nullable=False) # e.g., 'active', 'inactive'
    scraped_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Relationship to the property
    property = relationship("Property", back_populates="listings")
