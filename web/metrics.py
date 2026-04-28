from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from flask import Response

# Define metrics
HTTP_REQUESTS_TOTAL = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code']
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint']
)

HTTP_ERRORS_TOTAL = Counter(
    'http_errors_total',
    'Total number of HTTP error requests (4xx and 5xx)',
    ['method', 'endpoint', 'status_code']
)

def metrics_endpoint():
    """
    Returns the metrics in Prometheus format.
    """
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

def setup_metrics(app):
    """
    Registers the /metrics endpoint to the Flask app.
    """
    app.add_url_rule('/metrics', 'metrics', metrics_endpoint)
