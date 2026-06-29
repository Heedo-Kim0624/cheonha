from __future__ import annotations

from collections import deque
from datetime import datetime
from threading import Lock
from typing import Any
from uuid import uuid4

from django.utils import timezone


MAX_WORKFLOW_EVENTS = 500

_lock = Lock()
_events: deque[dict[str, Any]] = deque(maxlen=MAX_WORKFLOW_EVENTS)
_active_requests: dict[str, dict[str, Any]] = {}


def _now_iso() -> str:
    return timezone.now().isoformat()


def should_monitor_path(path: str) -> bool:
    if not path.startswith("/api/v1/"):
        return False
    if path.startswith("/api/v1/schema/") or path.startswith("/api/v1/docs/"):
        return False
    if path.startswith("/api/v1/dashboard/workflow-monitor/"):
        return False
    return True


def infer_channel(path: str) -> str:
    if path.startswith("/api/v1/mobile/"):
        return "mobile_app"
    if path.startswith("/api/v1/field-manager/"):
        return "field_manager_app"
    if path.startswith("/api/v1/vehicle/"):
        return "vehicle_portal"
    if path.startswith("/api/v1/tracking/"):
        return "tracking"
    if path.startswith("/api/v1/points/"):
        return "points"
    return "web_portal"


def record_request_start(method: str, path: str, query_string: str = "", meta: dict[str, Any] | None = None) -> str:
    request_id = str(uuid4())
    event = {
        "request_id": request_id,
        "method": method.upper(),
        "path": path,
        "query_string": query_string,
        "channel": infer_channel(path),
        "started_at": _now_iso(),
        "meta": meta or {},
    }
    with _lock:
        _active_requests[request_id] = event
    return request_id


def record_request_end(request_id: str, status_code: int, duration_ms: int, meta: dict[str, Any] | None = None) -> None:
    with _lock:
        started = _active_requests.pop(request_id, None)
        if started is None:
            return
        event = {
            **started,
            "status_code": status_code,
            "ok": 200 <= status_code < 400,
            "duration_ms": duration_ms,
            "ended_at": _now_iso(),
            "meta": {
                **started.get("meta", {}),
                **(meta or {}),
            },
        }
        _events.appendleft(event)


def snapshot() -> dict[str, Any]:
    with _lock:
        active_requests = [
            {
                **item,
                "age_ms": max(
                    0,
                    int((timezone.now() - datetime.fromisoformat(item["started_at"])).total_seconds() * 1000),
                ),
            }
            for item in _active_requests.values()
        ]
        recent_events = list(_events)

    return {
        "generated_at": _now_iso(),
        "active_requests": sorted(active_requests, key=lambda item: item["started_at"], reverse=True),
        "recent_events": recent_events,
        "stats": {
            "active_count": len(active_requests),
            "recent_count": len(recent_events),
            "success_count": sum(1 for event in recent_events if event["ok"]),
            "error_count": sum(1 for event in recent_events if not event["ok"]),
        },
    }
