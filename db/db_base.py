import os
import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from .models import Base

logger = logging.getLogger(__name__)

# Load environment variables (only once at module import)
load_dotenv()


# Select database config based on ENVIRONMENT
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    DB_CONFIG = {
        "user": os.getenv("PRODUCTION_DB_USER"),
        "password": os.getenv("PRODUCTION_DB_PASSWORD"),
        "host": os.getenv("PRODUCTION_DB_HOST"),
        "port": os.getenv("PRODUCTION_DB_PORT"),
        "dbname": os.getenv("PRODUCTION_DB_NAME"),
    }
    # Validate production config
    required_keys = ["user", "password", "host", "port", "dbname"]
    missing_keys = [k for k in required_keys if not DB_CONFIG[k]]
    if missing_keys:
        raise ValueError(f"Missing production database config: {missing_keys}")

    DATABASE_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
elif ENVIRONMENT == "development":
    # In serverless environments (Vercel), use /tmp for SQLite
    if os.getenv("VERCEL"):
        DATABASE_URL = "sqlite:////tmp/dev.db"
        logger.warning(
            "Using /tmp/dev.db for SQLite in serverless environment - data is ephemeral!"
        )
    else:
        DATABASE_URL = os.getenv("DEVELOPMENT_DATABASE_URL", "sqlite:///./dev.db")
else:
    raise ValueError(f"Unknown ENVIRONMENT: {ENVIRONMENT}")

logger.info(f"Database environment: {ENVIRONMENT}")

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Test connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=ENVIRONMENT == "development",  # Log SQL in development
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_tables_initialized = False


def ensure_tables():
    global _tables_initialized
    if not _tables_initialized:
        Base.metadata.create_all(bind=engine)
        _tables_initialized = True


def init_connection_pool():
    """
    Create tables if they don't exist.
    Initialize the database schema.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise


def close_all_connections():
    """
    Dispose of the engine and close all connections.
    """
    try:
        engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {str(e)}")


def get_db():
    """
    Dependency for database session.
    Usage: db: Session = Depends(get_db)
    """
    ensure_tables()
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


# For backward compatibility, keep get_cursor but use SQLAlchemy session
class CursorWrapper:
    """Wraps SQLAlchemy Session to provide cursor-like interface for raw SQL."""

    def __init__(self, session):
        self.session = session
        self.last_result = None
        self._lastrowid = None

    @property
    def lastrowid(self):
        """Get the last inserted row ID (for INSERT statements)."""
        if self._lastrowid is not None:
            return self._lastrowid
        # Try to get from last_result if available
        if self.last_result and hasattr(self.last_result, "lastrowid"):
            return self.last_result.lastrowid
        return None

    @staticmethod
    def _convert_positional(sql: str, params):
        """Convert `%s` placeholders to named parameters for SQLAlchemy text()."""
        parts = sql.split("%s")
        placeholder_count = len(parts) - 1
        if placeholder_count != len(params):
            raise ValueError(f"Expected {placeholder_count} params, got {len(params)}")
        bind_params = {}
        new_sql = parts[0]
        for idx, part in enumerate(parts[1:]):
            key = f"p{idx}"
            new_sql += f":{key}" + part
            bind_params[key] = params[idx]
        return new_sql, bind_params

    def execute(self, sql, params=None):
        """Execute raw SQL with parameter support."""
        try:
            # Convert to SQLAlchemy text() for SQLAlchemy 2.0 compatibility
            if params is None:
                stmt = text(sql)
                self.last_result = self.session.execute(stmt)
            elif isinstance(params, dict):
                stmt = text(sql)
                self.last_result = self.session.execute(stmt, params)
            else:
                converted_sql, bind_params = self._convert_positional(sql, list(params))
                stmt = text(converted_sql)
                self.last_result = self.session.execute(stmt, bind_params)

            # Store lastrowid if available (for INSERT operations)
            if self.last_result and hasattr(self.last_result, "lastrowid"):
                self._lastrowid = self.last_result.lastrowid
            elif self.last_result and hasattr(self.last_result, "inserted_primary_key"):
                # For SQLAlchemy 2.0
                pk = self.last_result.inserted_primary_key
                if pk:
                    self._lastrowid = pk[0] if isinstance(pk, tuple) else pk

        except Exception as e:
            logger.error(f"Error executing SQL: {str(e)}")
            raise

    def fetchall(self):
        """Fetch all results as list of Row objects (dict-like)."""
        if not self.last_result:
            return []
        return [dict(row._mapping) for row in self.last_result.fetchall()]

    def fetchone(self):
        """Fetch one result as Row object (dict-like)."""
        if not self.last_result:
            return None
        row = self.last_result.fetchone()
        return dict(row._mapping) if row else None

    def commit(self):
        """Commit transaction."""
        self.session.commit()

    def rollback(self):
        """Rollback transaction."""
        self.session.rollback()

    def query(self, *args, **kwargs):
        """Proxy to SQLAlchemy session.query for ORM usage."""
        return self.session.query(*args, **kwargs)

    def __getattr__(self, name):
        """Delegate unknown attributes to the underlying session."""
        return getattr(self.session, name)


@contextmanager
def get_cursor(commit=False):
    """
    Backward compatibility: yield a cursor-like wrapper around SQLAlchemy session.
    Converts raw SQL to use SQLAlchemy's text() for 2.0 compatibility.

    Usage:
        with get_cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            result = cur.fetchone()
    """
    ensure_tables()
    db = SessionLocal()
    cursor = CursorWrapper(db)
    try:
        yield cursor
        if commit:
            db.commit()
    except Exception as e:
        logger.error(f"Error in get_cursor: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_transaction_cursor():
    """
    For explicit transactions.
    Auto-rollback on exception.
    """
    ensure_tables()
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Transaction error, rolling back: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()
