from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
from app.models.transcription import Transcription
from app.models.user import User
from app.models.prompt import Prompt
from app.models.audio import AudioFile
from app.models.logs import Logs
from app.models.analysis import Analysis
from app.models.api_keys import APIKeys

def init_db(database_url):
    
    engine = create_engine(database_url, echo=False)
    Session = sessionmaker(bind=engine)
    # Создание всех таблиц
    Base.metadata.create_all(engine)

    return engine, Session, Base