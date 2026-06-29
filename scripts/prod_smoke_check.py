#!/usr/bin/env python
"""Read-only production smoke checks.

The checks are intentionally non-mutating. Authenticated API checks run only
when an admin bearer token is supplied through ADMIN_ACCESS_TOKEN.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from io import StringIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://43.201.160.163"


@dataclass(frozen=True)
class SmokeCheck:
    label: str
    path: str
    expected_status: int = 200
    expected_kind: str = "json"
    auth: bool = False


PUBLIC_CHECKS = (
    SmokeCheck("web root", "/", expected_kind="html"),
    SmokeCheck("privacy page", "/privacy/", expected_kind="html"),
    SmokeCheck("mobile app config", "/api/v1/mobile/app-config/", expected_kind="json"),
)


def default_date_range():
    end = date.today()
    start = end - timedelta(days=7)
    return start.isoformat(), end.isoformat()


def authenticated_checks(start_date, end_date):
    query = f"start={start_date}&end={end_date}&metric=boxes"
    return (
        SmokeCheck("teams", "/api/v1/accounts/teams/", auth=True),
        SmokeCheck("dashboard kpi", f"/api/v1/dashboard/dashboard/kpi/?start={start_date}&end={end_date}", auth=True),
        SmokeCheck("operation report", f"/api/v1/dispatch/uploads/operation-report/?{query}", auth=True),
        SmokeCheck("operation report map", f"/api/v1/dispatch/uploads/operation-report-yongcha-map/?{query}", auth=True),
        SmokeCheck("operation report csv", f"/api/v1/dispatch/uploads/operation-report-csv/?{query}", expected_kind="csv", auth=True),
        SmokeCheck("settlements", "/api/v1/settlement/settlements/?limit=1", auth=True),
    )


def join_url(base_url, path):
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def read_response(base_url, check, token=None, timeout=20):
    headers = {
        "Accept": "text/csv,*/*" if check.expected_kind == "csv" else "application/json,text/html",
        "User-Agent": "cheonha-prod-smoke/1.0",
    }
    if check.auth:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(join_url(base_url, check.path), headers=headers, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
            return response.status, response.headers.get("Content-Type", ""), body
    except HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", ""), exc.read()
    except URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc


def assert_response_shape(check, status, content_type, body):
    if status != check.expected_status:
        raise AssertionError(f"expected status {check.expected_status}, got {status}")

    sample = body[:200].decode("utf-8", errors="replace").lstrip()
    lower_type = content_type.lower()

    if check.expected_kind == "json":
        if sample.startswith("<"):
            raise AssertionError("API returned HTML instead of JSON")
        if "json" not in lower_type:
            raise AssertionError(f"expected JSON content-type, got {content_type}")
        json.loads(body.decode("utf-8-sig"))
    elif check.expected_kind == "csv":
        if sample.startswith("<"):
            raise AssertionError("CSV endpoint returned HTML")
        if "csv" not in lower_type:
            raise AssertionError(f"expected CSV content-type, got {content_type}")
        parsed = list(csv.reader(StringIO(body.decode("utf-8-sig"))))
        if not parsed or len(parsed[0]) < 4:
            raise AssertionError("CSV response has no usable header")
    elif check.expected_kind == "html":
        if "html" not in lower_type:
            raise AssertionError(f"expected HTML content-type, got {content_type}")


def run_checks(base_url, token, start_date, end_date):
    checks = list(PUBLIC_CHECKS)
    if token:
        checks.extend(authenticated_checks(start_date, end_date))
    else:
        print("ADMIN_ACCESS_TOKEN not set; skipping authenticated API checks.")

    failures = []
    for check in checks:
        try:
            status, content_type, body = read_response(base_url, check, token=token)
            assert_response_shape(check, status, content_type, body)
            print(f"PASS {check.label}: {status} {content_type}")
        except Exception as exc:
            failures.append(f"{check.label}: {exc}")
            print(f"FAIL {check.label}: {exc}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("PROD_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--token", default=os.environ.get("ADMIN_ACCESS_TOKEN", ""))
    parser.add_argument("--start", default="")
    parser.add_argument("--end", default="")
    args = parser.parse_args()

    start_date, end_date = (args.start, args.end) if args.start and args.end else default_date_range()
    failures = run_checks(args.base_url, args.token.strip(), start_date, end_date)
    if failures:
        print("\nProduction smoke failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("\nProduction smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
