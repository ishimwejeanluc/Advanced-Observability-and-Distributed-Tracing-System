
import os
import time
import logging
from flask import Flask, jsonify, request, g
import mysql.connector

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.mysql import MySQLInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

# Import our observability modules
from logging_config import setup_logging
from metrics import setup_metrics
from middleware import setup_observability

# 1. Setup Logging (as early as possible)
setup_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- OpenTelemetry Setup ---
resource = Resource(attributes={SERVICE_NAME: "advanced-monitoring-webapp"})
provider = TracerProvider(resource=resource)
trace.set_tracer_provider(provider)
jaeger_exporter = JaegerExporter(
    agent_host_name=os.getenv("JAEGER_AGENT_HOST", "jaeger"),
    agent_port=int(os.getenv("JAEGER_AGENT_PORT", 6831)),
)
span_processor = BatchSpanProcessor(jaeger_exporter)
provider.add_span_processor(span_processor)

FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()
MySQLInstrumentor().instrument()

# Inject trace/span IDs into logs
from opentelemetry.trace import get_current_span
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

def inject_trace_ids(record):
    span = get_current_span()
    if span and span.get_span_context().is_valid:
        record.trace_id = format(span.get_span_context().trace_id, '032x')
        record.span_id = format(span.get_span_context().span_id, '016x')
    else:
        record.trace_id = None
        record.span_id = None
    return True

logging.Logger.manager.loggerDict[logger.name].inject_trace_ids = inject_trace_ids

# 2. Setup Metrics and Observability Middleware
setup_metrics(app)
setup_observability(app)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "topics_db")
DB_USER = os.getenv("DB_USER", "appuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "appsecret")
DB_PORT = int(os.getenv("DB_PORT", "3306"))


def get_connection():
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


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/topics")
def list_topics():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, title, description, created_at FROM topics ORDER BY id")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(rows)


@app.post("/api/topics")
def create_topic():
    payload = request.get_json(silent=True) or {}
    title = payload.get("title")
    description = payload.get("description", "")

    if not title:
        return jsonify({"error": "title is required"}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "INSERT INTO topics (title, description) VALUES (%s, %s)",
        (title, description),
    )
    conn.commit()
    topic_id = cursor.lastrowid
    cursor.execute(
        "SELECT id, title, description, created_at FROM topics WHERE id = %s",
        (topic_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return jsonify(row), 201


@app.get("/api/topics/<int:topic_id>")
def get_topic(topic_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, title, description, created_at FROM topics WHERE id = %s",
        (topic_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row is None:
        return jsonify({"error": "topic not found"}), 404

    return jsonify(row)


@app.put("/api/topics/<int:topic_id>")
def update_topic(topic_id):
    payload = request.get_json(silent=True) or {}
    title = payload.get("title")
    description = payload.get("description")

    if title is None and description is None:
        return jsonify({"error": "title or description is required"}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id FROM topics WHERE id = %s", (topic_id,))
    existing = cursor.fetchone()
    if existing is None:
        cursor.close()
        conn.close()
        return jsonify({"error": "topic not found"}), 404

    if title is not None and description is not None:
        cursor.execute(
            "UPDATE topics SET title = %s, description = %s WHERE id = %s",
            (title, description, topic_id),
        )
    elif title is not None:
        cursor.execute(
            "UPDATE topics SET title = %s WHERE id = %s",
            (title, topic_id),
        )
    else:
        cursor.execute(
            "UPDATE topics SET description = %s WHERE id = %s",
            (description, topic_id),
        )

    conn.commit()
    cursor.execute(
        "SELECT id, title, description, created_at FROM topics WHERE id = %s",
        (topic_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return jsonify(row)


@app.delete("/api/topics/<int:topic_id>")
def delete_topic(topic_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM topics WHERE id = %s", (topic_id,))
    existing = cursor.fetchone()
    if existing is None:
        cursor.close()
        conn.close()
        return jsonify({"error": "topic not found"}), 404

    cursor.execute("DELETE FROM topics WHERE id = %s", (topic_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "deleted"})


if __name__ == "__main__":
    if not wait_for_db():
        logger.error("Database connection failed after retries. Exiting.")
        raise SystemExit("Database not ready")
    
    logger.info("Starting Flask application on port 5000")
    app.run(host="0.0.0.0", port=5000)
