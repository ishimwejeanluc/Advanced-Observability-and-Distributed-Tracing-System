import os
import time
import logging
import mysql.connector
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "topics_db")
DB_USER = os.getenv("DB_USER", "appuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "appsecret")
DB_PORT = int(os.getenv("DB_PORT", "3306"))


def get_connection():
    with tracer.start_as_current_span("db.connect") as span:
        span.set_attribute("db.host", DB_HOST)
        span.set_attribute("db.name", DB_NAME)
        span.set_attribute("db.port", DB_PORT)
        return mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT,
        )


def wait_for_db(retries=20, delay=3):
    logger.info("Waiting for database connection...", extra={"db_host": DB_HOST, "db_port": DB_PORT})
    for i in range(retries):
        try:
            conn = get_connection()
            conn.close()
            logger.info("Database connection established.")
            return True
        except mysql.connector.Error as e:
            logger.warning(f"Database not ready (attempt {i+1}/{retries}): {str(e)}")
            time.sleep(delay)
    return False
