import os
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.mysql import MySQLInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter


def setup_tracing(app):
    resource = Resource(attributes={SERVICE_NAME: "advanced-monitoring-webapp"})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    jaeger_exporter = JaegerExporter(
        agent_host_name=os.getenv("JAEGER_AGENT_HOST", "jaeger"),
        agent_port=int(os.getenv("JAEGER_AGENT_PORT", 6831)),
    )
    provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

    FlaskInstrumentor().instrument_app(app)
    RequestsInstrumentor().instrument()
    MySQLInstrumentor().instrument()
