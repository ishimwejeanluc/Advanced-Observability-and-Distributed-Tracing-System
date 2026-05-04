import logging
import sys
from pythonjsonlogger import jsonlogger
from datetime import datetime


class TraceContextFilter(logging.Filter):
    """Stamps trace_id and span_id from the active OTel span onto every log record."""
    def filter(self, record):
        from opentelemetry.trace import get_current_span
        span = get_current_span()
        ctx = span.get_span_context() if span else None
        if ctx and ctx.is_valid:
            record.trace_id = format(ctx.trace_id, '032x')
            record.span_id = format(ctx.span_id, '016x')
        else:
            record.trace_id = None
            record.span_id = None
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        log_record['level'] = record.levelname
        if getattr(record, 'trace_id', None):
            log_record['trace_id'] = record.trace_id
        if getattr(record, 'span_id', None):
            log_record['span_id'] = record.span_id


def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s'))
    handler.addFilter(TraceContextFilter())

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
