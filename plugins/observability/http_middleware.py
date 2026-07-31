"""Minimal HTTP tracing and metrics middleware without external services."""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware


class ObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, metrics):
        super().__init__(app)
        self.metrics = metrics

    async def dispatch(self, request, call_next):
        trace_id = request.headers.get("x-trace-id") or uuid.uuid4().hex
        request.state.trace_id = trace_id
        started = time.monotonic()
        self.metrics.inc("http_requests_total")
        try:
            response = await call_next(request)
        except Exception:
            self.metrics.inc("http_errors_total")
            raise
        duration = (time.monotonic() - started) * 1000
        self.metrics.observe("http_request_duration_ms", duration)
        self.metrics.inc(f"http_status_{response.status_code}")
        if response.status_code >= 500:
            self.metrics.inc("http_errors_total")
        response.headers["X-Trace-ID"] = trace_id
        return response
