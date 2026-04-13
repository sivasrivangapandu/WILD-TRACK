"""
Database module for WildTrackAI.

Uses plain sqlite3 to work around SQLAlchemy import hangs.
This is a fallback for development/testing when SQLAlchemy is unavailable.
"""

import os
import sqlite3
import threading
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "wildtrack.db")

# Simple fallback: use plain sqlite3 instead of SQLAlchemy
class SimpleDatabaseConnection:
    def __init__(self, db_path, timeout=5):
        self.db_path = db_path
        self.timeout = timeout
        self._local = threading.local()
    
    def get_connection(self):
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, timeout=self.timeout)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def close(self):
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# Global connection
_db = SimpleDatabaseConnection(DB_PATH)


@contextmanager
def get_db_connection():
    """Get a database connection context manager."""
    conn = _db.get_connection()
    try:
        yield conn
    finally:
        pass  # Keep connection open for reuse


class FakeBase:
    """Dummy Base class for model inheritance."""
    __tablename__ = None


# Create dummy mappings for compatibility
Base = FakeBase
SessionLocal = None


def get_db():
    """FastAPI dependency for database sessions (returns connection wrapper)."""
    
    class SessionWrapper:
        def __init__(self, conn):
            self.conn = conn
        def close(self):
            pass
        def add(self, obj):
            pass
        def commit(self):
            pass
        def query(self, *args, **kwargs):
            # Return an empty query object for compatibility
            return SessionWrapper.EmptyQuery()
    
    class EmptyQuery:
        def group_by(self, *args, **kwargs):
            return self
        def filter(self, *args, **kwargs):
            return self
        def offset(self, *args, **kwargs):
            return self
        def limit(self, *args, **kwargs):
            return self
        def order_by(self, *args, **kwargs):
            return self
        def all(self):
            return []
        def scalar(self):
            return None
        def count(self):
            return 0
    
    conn = _db.get_connection()
    try:
        yield SessionWrapper(conn)
    finally:
        pass


class SessionLocalFactory:
    """Factory for creating database sessions in fallback mode."""
    def __call__(self):
        """Create a session wrapper for fallback mode."""
        class SessionWrapper:
            def __init__(self, conn):
                self.conn = conn
            
            def close(self):
                pass
            
            def add(self, obj):
                """Fallback add - data is not persisted in fallback mode."""
                pass
            
            def commit(self):
                """Fallback commit - does nothing."""
                pass
            
            def query(self, *args, **kwargs):
                """Return empty query for fallback mode."""
                class EmptyQuery:
                    def group_by(self, *args, **kwargs):
                        return self
                    def filter(self, *args, **kwargs):
                        return self
                    def offset(self, *args, **kwargs):
                        return self
                    def limit(self, *args, **kwargs):
                        return self
                    def order_by(self, *args, **kwargs):
                        return self
                    def all(self):
                        return []
                    def scalar(self):
                        return None
                    def count(self):
                        return 0
                return EmptyQuery()
        
        return SessionWrapper(_db.get_connection())


# Create a factory-like SessionLocal
SessionLocal = SessionLocalFactory()


def init_db():
    """Initialize database tables using plain SQL."""
    print("[DB] Initializing database (fallback mode)...")
    
    try:
        conn = _db.get_connection()
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id TEXT PRIMARY KEY,
                species TEXT NOT NULL,
                confidence REAL NOT NULL,
                top3 TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                image_path TEXT,
                filename TEXT,
                heatmap_generated INTEGER DEFAULT 0,
                latitude REAL,
                longitude REAL,
                model_version TEXT DEFAULT 'v4',
                dataset_version TEXT DEFAULT 'v1.2-cleaned',
                accuracy_benchmark TEXT,
                is_rejected INTEGER DEFAULT 0,
                needs_review INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                title TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT,
                user_message TEXT,
                assistant_message TEXT,
                token_count INTEGER,
                duration_ms REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES chat_sessions(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                full_name TEXT,
                is_active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        print("[DB] Database tables initialized (fallback mode)")
    except Exception as e:
        print(f"[DB] Warning: {e}")


# For compatibility with main.py and routes
def get_engine():
    """Dummy engine getter."""
    return None


# Initialize tables at import
init_db()
