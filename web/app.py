import logging
from flask import Flask

from logging_config import setup_logging
from tracing import setup_tracing
from metrics import setup_metrics
from middleware import setup_observability
from database import wait_for_db
from routes import bp

setup_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__)

setup_tracing(app)
setup_metrics(app)
setup_observability(app)
app.register_blueprint(bp)

if __name__ == "__main__":
    if not wait_for_db():
        logger.error("Database connection failed after retries. Exiting.")
        raise SystemExit("Database not ready")

    logger.info("Starting Flask application on port 5000")
    app.run(host="0.0.0.0", port=5000)
