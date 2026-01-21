"""
Database connection management for F1 telemetry database.

This module handles SQLite database initialization, connection pooling,
and session management using SQLAlchemy.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from .models import Base

# Database file location (in project root)
DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'f1_telemetry.db')

# Global engine and session factory
_engine = None
_session_factory = None


def init_database(database_path=None):
    """
    Initialize the database connection and create tables if they don't exist.
    
    Args:
        database_path: Optional custom path for the database file.
                      Defaults to 'f1_telemetry.db' in project root.
    
    Returns:
        SQLAlchemy engine instance
    """
    global _engine, _session_factory
    
    if database_path is None:
        database_path = DATABASE_PATH
    
    # Create database directory if it doesn't exist
    db_dir = os.path.dirname(database_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    # Create engine with SQLite
    # echo=False disables SQL logging (set to True for debugging)
    _engine = create_engine(
        f'sqlite:///{database_path}',
        echo=False,
        connect_args={'check_same_thread': False}  # Allow multi-threading
    )
    
    # Create all tables
    Base.metadata.create_all(_engine)
    
    # Create session factory
    _session_factory = scoped_session(sessionmaker(bind=_engine))
    
    print(f"Database initialized at: {database_path}")
    return _engine


def get_session():
    """
    Get a database session for performing operations.
    
    Returns:
        SQLAlchemy session instance
    
    Raises:
        RuntimeError: If database has not been initialized
    """
    global _session_factory
    
    if _session_factory is None:
        # Auto-initialize if not already done
        init_database()
    
    return _session_factory()


def close_session(session):
    """
    Close a database session.
    
    Args:
        session: SQLAlchemy session to close
    """
    if session:
        session.close()


def get_engine():
    """
    Get the database engine instance.
    
    Returns:
        SQLAlchemy engine instance
    
    Raises:
        RuntimeError: If database has not been initialized
    """
    global _engine
    
    if _engine is None:
        init_database()
    
    return _engine
