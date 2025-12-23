from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class Panel(Base):
    __tablename__ = 'panels'
    id = Column(Integer, primary_key=True)
    panel_id = Column(String, unique=True, nullable=False)
    sequence_no = Column(Integer, nullable=False)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    width = Column(Float, nullable=False) # Assuming fixed width/height for simplicity or stored if variable
    height = Column(Float, nullable=False)

class AnalysisConfig(Base):
    __tablename__ = 'analysis_config'
    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)

class Recipient(Base):
    __tablename__ = 'recipients'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String)

# Database Setup
DATABASE_URL = "sqlite:///db/grid_analysis.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
