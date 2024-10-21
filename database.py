# database.py

from sqlalchemy import Boolean, Column, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///zolanew_admin.db"  # Removed async
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# User model
class User(Base):
    __tablename__ = "users"

    userid = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)

# New Post model
class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    template_name = Column(String, index=True)
    category = Column(String, index=True)
    subcategory = Column(String, index=True, nullable=True)
    description = Column(Text)
    draft = Column(Boolean, default=False)
    content = Column(Text)
    date_created = Column(String)  # Store date as string for simplicity

# Database initialization
def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
