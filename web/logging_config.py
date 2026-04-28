import logging
import sys
from pythonjsonlogger import jsonlogger
from datetime import datetime


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['timestamp'] = now
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname
        # Add trace_id and span_id if present in the log record
        if hasattr(record, 'trace_id') and record.trace_id:
            log_record['trace_id'] = record.trace_id
        if hasattr(record, 'span_id') and record.span_id:
            log_record['span_id'] = record.span_id

def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    
    # Optional: Disable default flask/werkzeug logs if they are too noisy, 
    # or let them be processed by our root logger.
    # logging.getLogger('werkzeug').setLevel(logging.ERROR)
