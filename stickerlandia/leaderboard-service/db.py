import logging
import os
import psycopg2
from psycopg2 import pool

logger = logging.getLogger(__name__)

_connection_pool = None

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")


def get_connection_pool():
    global _connection_pool
    if _connection_pool is None:
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            _connection_pool = pool.SimpleConnectionPool(1, 5, dsn=database_url)
        else:
            _connection_pool = pool.SimpleConnectionPool(
                1, 5,
                host=os.environ.get("DATABASE_HOST", "localhost"),
                port=int(os.environ.get("DATABASE_PORT", "5432")),
                user=os.environ.get("DATABASE_USER", "postgres"),
                password=os.environ.get("DATABASE_PASSWORD", ""),
                dbname=os.environ.get("DATABASE_NAME", "stickerlandia"),
            )
    return _connection_pool


def get_connection():
    return get_connection_pool().getconn()


def put_connection(conn):
    get_connection_pool().putconn(conn)


def run_migrations():
    """Run all SQL migration files from the migrations directory."""
    if not os.path.isdir(MIGRATIONS_DIR):
        logger.warning("No migrations directory found at %s", MIGRATIONS_DIR)
        return

    migration_files = sorted(f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql"))
    if not migration_files:
        logger.info("No migration files found")
        return

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for filename in migration_files:
                filepath = os.path.join(MIGRATIONS_DIR, filename)
                with open(filepath) as f:
                    sql = f.read()
                logger.info("Running migration: %s", filename)
                cur.execute(sql)
        conn.commit()
        logger.info("All migrations completed successfully")
    except Exception:
        conn.rollback()
        logger.error("Migration failed", exc_info=True)
        raise
    finally:
        put_connection(conn)
