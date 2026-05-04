import time
import logging
from flask import request, g
from werkzeug.exceptions import HTTPException
from opentelemetry import trace
from opentelemetry.trace import StatusCode
from metrics import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION_SECONDS, HTTP_ERRORS_TOTAL

logger = logging.getLogger(__name__)

def start_timer():
    g.start_time = time.time()

def record_metrics(response):
    # Calculate latency
    latency = time.time() - g.start_time
    
    # Get request details
    endpoint = request.endpoint or "unknown"
    method = request.method
    status_code = response.status_code

    # Update Prometheus metrics
    HTTP_REQUESTS_TOTAL.labels(
        method=method, 
        endpoint=endpoint, 
        status_code=status_code
    ).inc()
    
    if status_code >= 400:
        span = trace.get_current_span()
        if span and span.is_recording():
            span.set_status(StatusCode.ERROR, f"HTTP {status_code}")

        ctx = span.get_span_context() if span else None
        exemplar = {'trace_id': format(ctx.trace_id, '032x')} if ctx and ctx.is_valid else None

        HTTP_ERRORS_TOTAL.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc(exemplar=exemplar)

        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=method,
            endpoint=endpoint
        ).observe(latency, exemplar=exemplar)
    else:
        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=method,
            endpoint=endpoint
        ).observe(latency)

    # Log request details in structured format
    # The logger is already configured to output JSON
    logger.info(
        f"Request processed: {method} {request.path} {status_code}",
        extra={
            "method": method,
            "endpoint": endpoint,
            "path": request.path,
            "status_code": status_code,
            "latency": latency,
            "remote_addr": request.remote_addr
        }
    )

    return response

def setup_observability(app):
    """
    Registers hooks for request instrumentation.
    """
    app.before_request(start_timer)
    app.after_request(record_metrics)
    
    

    @app.errorhandler(Exception)
    def handle_exception(e):
        if isinstance(e, HTTPException):
            return e

        span = trace.get_current_span()
        span.record_exception(e)
        span.set_status(StatusCode.ERROR, str(e))

        logger.exception(f"Unhandled Exception: {str(e)}", extra={
            "method": request.method,
            "path": request.path,
            "endpoint": request.endpoint
        })

        return {"error": "Internal Server Error"}, 500
