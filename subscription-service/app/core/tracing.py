"""OpenTelemetry tracing helper.

Wires FastAPI + httpx + SQLAlchemy instrumentation when OTEL_EXPORTER_OTLP_ENDPOINT
is set. Best-effort: if any otel package is missing the function is a no-op so
the service still boots.
"""
from __future__ import annotations

import os


def init_tracing(app, service_name: str) -> None:
    """Initialize OTel tracing if OTEL_EXPORTER_OTLP_ENDPOINT is set."""
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
        processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="/health,/ready,/metrics,/docs,/openapi.json",
        )
        HTTPXClientInstrumentor().instrument()
    except Exception:
        # Tracing is optional — never block service startup
        pass
