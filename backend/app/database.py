from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker , DeclarativeBase

#The url of the database
DATABASE_URL = "postgresql://admin:admin123@postgres:5432/cityfix"

#creating a reuseable engine
engine = create_engine(DATABASE_URL)

#create the session per request
SessionLocal = sessionmaker(
    autocommit =False,
    autoflush=False,
    bind=engine
)

class Base(DeclarativeBase):
    pass