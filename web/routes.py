from flask import Blueprint, jsonify, request
from opentelemetry import trace
from database import get_connection

bp = Blueprint("topics", __name__)
tracer = trace.get_tracer(__name__)


@bp.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@bp.get("/api/topics")
def list_topics():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, title, description, created_at FROM topics ORDER BY id")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(rows)


@bp.post("/api/topics")
def create_topic():
    with tracer.start_as_current_span("validate_input") as span:
        payload = request.get_json(silent=True) or {}
        title = payload.get("title")
        description = payload.get("description", "")
        span.set_attribute("input.title_present", bool(title))
        if not title:
            span.set_attribute("validation.error", "title is required")
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


@bp.get("/api/topics/<int:topic_id>")
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


@bp.put("/api/topics/<int:topic_id>")
def update_topic(topic_id):
    with tracer.start_as_current_span("validate_input") as span:
        payload = request.get_json(silent=True) or {}
        title = payload.get("title")
        description = payload.get("description")
        span.set_attribute("input.has_title", title is not None)
        span.set_attribute("input.has_description", description is not None)
        if title is None and description is None:
            span.set_attribute("validation.error", "title or description is required")
            return jsonify({"error": "title or description is required"}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id FROM topics WHERE id = %s", (topic_id,))
    if cursor.fetchone() is None:
        cursor.close()
        conn.close()
        return jsonify({"error": "topic not found"}), 404

    if title is not None and description is not None:
        cursor.execute(
            "UPDATE topics SET title = %s, description = %s WHERE id = %s",
            (title, description, topic_id),
        )
    elif title is not None:
        cursor.execute("UPDATE topics SET title = %s WHERE id = %s", (title, topic_id))
    else:
        cursor.execute("UPDATE topics SET description = %s WHERE id = %s", (description, topic_id))

    conn.commit()
    cursor.execute(
        "SELECT id, title, description, created_at FROM topics WHERE id = %s",
        (topic_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return jsonify(row)


@bp.delete("/api/topics/<int:topic_id>")
def delete_topic(topic_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM topics WHERE id = %s", (topic_id,))
    if cursor.fetchone() is None:
        cursor.close()
        conn.close()
        return jsonify({"error": "topic not found"}), 404

    cursor.execute("DELETE FROM topics WHERE id = %s", (topic_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "deleted"})
