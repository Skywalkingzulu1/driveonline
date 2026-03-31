import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Determine database URL from environment or fallback to a local SQLite file
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///app.db')

# Create engine and session factory
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()

# Example placeholder model (not used in current logic but ensures the module is functional)
# class User(Base):
#     __tablename__ = "users"
#     id = Column(Integer, primary_key=True, index=True)
#     email = Column(String, unique=True, index=True, nullable=False)
#     password_hash = Column(String, nullable=False)
#     is_verified = Column(Boolean, default=False)

# Create tables if they do not exist (no‑op for SQLite if file missing)
def init_db():
    Base.metadata.create_all(bind=engine)

# Initialize on import
init_db()
