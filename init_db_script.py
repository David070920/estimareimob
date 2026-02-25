import asyncio
from database import init_db
from models import Base

async def main():    
    print("Initializing database tables...")    
    await init_db(Base.metadata)    
    print("Database tables created successfully.")

if __name__ == "__main__":    
    asyncio.run(main())