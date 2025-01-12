# src/database.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import time
import logging

logger = logging.getLogger(__name__)

# Create the database instance
db = SQLAlchemy()


def wait_for_db(app, max_retries=30, retry_interval=2):
    """Wait for database to be ready"""
    retries = 0
    while retries < max_retries:
        try:
            # Try to connect to the database
            with app.app_context():
                db.session.execute(text("SELECT 1"))
                logger.info("Successfully connected to the database")
                return True
        except Exception as e:
            retries += 1
            if retries == max_retries:
                logger.error(f"Could not connect to database after {max_retries} retries: {str(e)}")
                raise
            logger.warning(f"Database not ready (attempt {retries}/{max_retries}): {str(e)}")
            time.sleep(retry_interval)
    return False


def init_db(app):
    """Initialize the database with the app"""
    # Initialize the SQLAlchemy app
    db.init_app(app)

    # Wait for database to be ready
    wait_for_db(app)

    # Create tables
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
            raise

    return db
