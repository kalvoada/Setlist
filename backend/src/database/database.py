from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Connection String
SQLALCHEMY_DATABASE_URL = "sqlite:///./social.db"

# 2. The Engine (The core connection)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 3. The Session Factory (Creates a new database session for each request)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. The Base Class (All models inherit from this)
Base = declarative_base()

# 5. Dependency (Used in routers to get a DB session)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()