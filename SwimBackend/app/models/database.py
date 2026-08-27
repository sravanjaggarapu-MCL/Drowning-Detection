# ============================================================
# FILE: database.py
#
# PURPOSE:
# This file configures the SQLite database connection for the
# PoolGuard backend.
#
# RESPONSIBILITIES:
# - Create the SQLite database connection.
# - Create the SQLAlchemy engine.
# - Create a database session factory.
# - Provide database sessions to the application.
#
# IMPORTANT:
# - This file does NOT define detection data.
# - Database table definitions belong in model files.
# - Business logic does NOT belong here.
#
# DATABASE:
# SQLite is being used initially because it is simple and
# requires no separate database server.
#
# FUTURE:
# The database can later be migrated to PostgreSQL/MySQL
# without changing the API architecture significantly.
# ============================================================

from sqlalchemy import create_engine # creates database connection between the application and the database
from sqlalchemy.orm import sessionmaker # creates a session


# SQLite database file.
#
# The database will be created inside the data directory.
DATABASE_URL = "sqlite:///./data/poolguard.db"


# Create the SQLAlchemy engine.
#
# The engine manages the connection between our application
# and the SQLite database.
engine = create_engine(
    DATABASE_URL,
    connect_args={
        # SQLite requires this option when the database is
        # accessed from FastAPI's request-handling threads.
        "check_same_thread": False
    }
)


# Create a session factory.
#
# A session is used whenever we need to read or write data
# in the database.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    """
    Provide a database session to the application.

    The session is automatically closed after the operation
    finishes, even if an error occurs.
    """

    # Create a new database session.
    db = SessionLocal()

    try:
        # Give the session to the caller.
        yield db

    finally:
        # Always close the session after the request finishes.
        db.close()