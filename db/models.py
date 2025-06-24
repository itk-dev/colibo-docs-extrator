# db/models.py
from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class SyncedDocument(Base):
    """Model to track synced documents between Colibo and OpenWebUI."""

    __tablename__ = "synced_documents"

    id = Column(Integer, primary_key=True)
    colibo_doc_id = Column(Integer, nullable=False, unique=True, index=True)
    webui_doc_id = Column(String, nullable=False)
    knowledge_id = Column(String, nullable=False)
    last_synced = Column(DateTime, nullable=False
)

    def __repr__(self):
        return f"<SyncedDocument(colibo_id={self.colibo_doc_id}, webui_id={self.webui_doc_id})>"


class TokenCache(Base):
    """Model to cache API tokens."""

    __tablename__ = "token_cache"

    id = Column(Integer, primary_key=True)
    service_name = Column(String, nullable=False, unique=True, index=True)
    access_token = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    def is_valid(self, buffer_seconds=60):
        """Check if the token is still valid with a safety buffer."""
        now = datetime.now(timezone.utc)
        # Ensure expires_at has timezone info
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now < expires - timedelta(seconds=buffer_seconds)


def get_engine(db_path="sqlite:///sync.db"):
    """Create and return a database engine."""
    return create_engine(db_path)


def get_session(engine=None):
    """Create and return a session factory bound to the engine."""
    if engine is None:
        engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def init_db(db_path="sqlite:///sync.db"):
    """Initialize the database, creating tables if they don't exist."""
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine
