from __future__ import annotations

import time

from .workflow_monitor import record_request_end, record_request_start, should_monitor_path


class WorkflowMonitorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        request_id = None
        started_at = time.perf_counter()

        if should_monitor_path(path):
            request_id = record_request_start(
                method=request.method,
                path=path,
                query_string=request.META.get("QUERY_STRING", ""),
                meta={
                    "ip": request.META.get("REMOTE_ADDR", ""),
                    "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
                },
            )

        try:
            response = self.get_response(request)
        except Exception:
            if request_id:
                duration_ms = int((time.perf_counter() - started_at) * 1000)
                record_request_end(
                    request_id=request_id,
                    status_code=500,
                    duration_ms=duration_ms,
                )
            raise

        if request_id:
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            record_request_end(
                request_id=request_id,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
        return response
