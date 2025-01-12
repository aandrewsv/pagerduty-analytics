from flask import Flask
from flask_smorest import Api
from src.database import init_db
from src.api.routes import blp
import os
from dotenv import load_dotenv
import logging


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


def create_app():
    app = Flask(__name__)

    # Configure the Flask application
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "mysql+pymysql://user:password@db/pagerduty_analytics")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["PAGERDUTY_API_KEY"] = os.getenv("PAGERDUTY_API_KEY")

    # Configure Flask-Smorest
    app.config["API_TITLE"] = "PagerDuty Analytics API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.2"
    app.config["OPENAPI_URL_PREFIX"] = "/"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = "/api/docs"
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    if not app.config["PAGERDUTY_API_KEY"]:
        raise ValueError("PAGERDUTY_API_KEY environment variable is required")

    # Initialize database
    init_db(app)

    # Initialize API with Flask-Smorest
    api = Api(app)
    api.register_blueprint(blp)

    return app


# Create the Flask application instance
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
