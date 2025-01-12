import pytest
from flask import Flask
from src.database import init_db, db
from datetime import datetime, timezone
from src.api.routes import blp

@pytest.fixture
def app():
    """Create and configure a test Flask application."""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = True
    app.config["API_TITLE"] = "Test API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.2"
    app.config["OPENAPI_URL_PREFIX"] = "/"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = "/api/docs"
    
    init_db(app)
    app.register_blueprint(blp)
    
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def db_session(app):
    """Create a fresh database session."""
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.remove()
        db.drop_all()

# Utility fixture para fechas
@pytest.fixture
def utc_now():
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)
