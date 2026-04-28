import time
import logging
from flask import request, g
from werkzeug.exceptions import HTTPException
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
    
    # Increment error counter if status is 4xx or 5xx
    if status_code >= 400:
        HTTP_ERRORS_TOTAL.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc()
    
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
        # Log the exception with stack trace
        logger.exception(f"Unhandled Exception: {str(e)}", extra={
            "method": request.method,
            "path": request.path,
            "endpoint": request.endpoint
        })
        
        # We still want to record metrics for this failure
        # Flask usually doesn't call after_request if an exception is raised 
        # but if we have an error handler, it returns a response which then goes through after_request.
        # However, to be safe, we can manually trigger it or let Flask handle it.
        # In modern Flask, after_request is called after the error handler.
        
        return {"error": "Internal Server Error"}, 500
