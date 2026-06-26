#!/usr/bin/env python
"""Static regression gate for high-risk user-facing flows.

This script does not call production services or mutate files. It inspects the
live Django URL resolver and the button/API map so refactors can fail fast when
they accidentally remove or reclassify critical endpoints.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import api_audit  # noqa: E402


@dataclass(frozen=True)
class RequiredRoute:
    label: str
    method: str
    path: str
    exposure: str | None = None


REQUIRED_ROUTES = (
    RequiredRoute("ERP login", "POST", "api/v1/auth/login/", "public"),
    RequiredRoute("ERP logout", "POST", "api/v1/auth/logout/", "public"),
    RequiredRoute("ERP profile", "GET", "api/v1/auth/profile/", "jwt-authenticated"),
    RequiredRoute("team list", "GET", "api/v1/accounts/teams/", "jwt-authenticated"),
    RequiredRoute("dashboard KPI", "GET", "api/v1/dashboard/dashboard/kpi/", "jwt-authenticated"),
    RequiredRoute("crew list", "GET", "api/v1/crew/members/", "jwt-authenticated"),
    RequiredRoute("crew update", "PATCH", "api/v1/crew/members/{id}/", "jwt-authenticated"),
    RequiredRoute("regular to yongcha", "POST", "api/v1/crew/members/{id}/convert_to_yongcha/", "jwt-authenticated"),
    RequiredRoute("yongcha to regular", "POST", "api/v1/crew/members/{id}/convert_to_regular/", "jwt-authenticated"),
    RequiredRoute("dispatch upload list", "GET", "api/v1/dispatch/uploads/", "jwt-authenticated"),
    RequiredRoute("dispatch upload create", "POST", "api/v1/dispatch/uploads/", "jwt-authenticated"),
    RequiredRoute("dispatch detected info", "GET", "api/v1/dispatch/uploads/{id}/detected_info/", "jwt-authenticated"),
    RequiredRoute("dispatch configure", "POST", "api/v1/dispatch/uploads/{id}/configure/", "jwt-authenticated"),
    RequiredRoute("dispatch set overtime", "POST", "api/v1/dispatch/uploads/{id}/set_overtime/", "jwt-authenticated"),
    RequiredRoute("dispatch finalize", "POST", "api/v1/dispatch/uploads/{id}/finalize/", "jwt-authenticated"),
    RequiredRoute("operation report", "GET", "api/v1/dispatch/uploads/operation-report/", "jwt-authenticated"),
    RequiredRoute("operation report CSV", "GET", "api/v1/dispatch/uploads/operation-report-csv/", "jwt-authenticated"),
    RequiredRoute("operation report yongcha map", "GET", "api/v1/dispatch/uploads/operation-report-yongcha-map/", "jwt-authenticated"),
    RequiredRoute("settlement list", "GET", "api/v1/settlement/settlements/", "jwt-authenticated"),
    RequiredRoute("settlement export", "GET", "api/v1/settlement/settlements/{id}/export/", "jwt-authenticated"),
    RequiredRoute("settlement details", "GET", "api/v1/settlement/details/", "jwt-authenticated"),
    RequiredRoute("points summaries", "GET", "api/v1/points/summaries/", "jwt-authenticated"),
    RequiredRoute("points item create", "POST", "api/v1/points/items/", "jwt-authenticated"),
    RequiredRoute("tracking live status", "GET", "api/v1/tracking/live-status/", "jwt-authenticated"),
    RequiredRoute("tracking usage overview", "GET", "api/v1/tracking/usage-overview/", "jwt-authenticated"),
    RequiredRoute("tracking CSV", "GET", "api/v1/tracking/sessions/{id}/download_csv/", "jwt-authenticated"),
    RequiredRoute("vehicle list", "GET", "api/v1/vehicle/vehicles/", "jwt-authenticated"),
    RequiredRoute("vehicle stats", "GET", "api/v1/vehicle/vehicles/stats/", "jwt-authenticated"),
    RequiredRoute("mobile config", "GET", "api/v1/mobile/app-config/", "public"),
    RequiredRoute("mobile login", "POST", "api/v1/mobile/login/", "public"),
    RequiredRoute("mobile register", "POST", "api/v1/mobile/register/", "public"),
    RequiredRoute("mobile profile", "GET", "api/v1/mobile/profile/", "custom-mobile-token"),
    RequiredRoute("mobile password", "POST", "api/v1/mobile/password/", "custom-mobile-token"),
    RequiredRoute("mobile vehicle number", "POST", "api/v1/mobile/vehicle-number/", "custom-mobile-token"),
    RequiredRoute("mobile payroll account", "POST", "api/v1/mobile/payroll-account/", "custom-mobile-token"),
    RequiredRoute("mobile settlements", "GET", "api/v1/mobile/settlements/", "custom-mobile-token"),
    RequiredRoute("mobile inquiry", "GET", "api/v1/mobile/settlement-inquiry/", "custom-mobile-token"),
    RequiredRoute("mobile work start", "POST", "api/v1/mobile/work-session/start/", "custom-mobile-token"),
    RequiredRoute("mobile work stop", "POST", "api/v1/mobile/work-session/stop/", "custom-mobile-token"),
    RequiredRoute("mobile work upload", "POST", "api/v1/mobile/work-session/upload/", "custom-mobile-token"),
    RequiredRoute("field manager login", "POST", "api/v1/field-manager/login/", "public"),
    RequiredRoute("field manager subscription", "POST", "api/v1/field-manager/subscription-requests/", "custom-field-manager-token"),
    RequiredRoute("field manager return", "POST", "api/v1/field-manager/return-requests/", "custom-field-manager-token"),
    RequiredRoute("field manager AS", "POST", "api/v1/field-manager/as-requests/", "custom-field-manager-token"),
)

BUTTON_MAP_REFERENCES = (
    "/auth/login/",
    "/crew/members",
    "/dispatch/uploads",
    "/dispatch/uploads/operation-report",
    "/settlement/settlements",
    "/tracking/usage-overview",
    "/points/summaries",
    "/vehicle/vehicles",
    "/mobile/login",
    "/field-manager/login",
)


def collect_business_routes():
    api_audit.configure_django()
    return api_audit.business_rows(api_audit.collect_routes())


def check_required_routes(rows):
    by_key = {(row.method, row.path): row for row in rows}
    failures = []

    for required in REQUIRED_ROUTES:
        row = by_key.get((required.method, required.path))
        if row is None:
            failures.append(f"missing route: {required.method} {required.path} ({required.label})")
            continue
        if required.exposure and row.exposure != required.exposure:
            failures.append(
                f"exposure changed: {required.method} {required.path} "
                f"expected={required.exposure} actual={row.exposure} ({required.label})"
            )

    return failures


def check_button_map_references():
    path = ROOT / "BUTTON_API_MAP.md"
    if not path.exists():
        return ["missing file: BUTTON_API_MAP.md"]

    text = path.read_text(encoding="utf-8")
    return [
        f"BUTTON_API_MAP.md missing reference: {reference}"
        for reference in BUTTON_MAP_REFERENCES
        if reference not in text
    ]


def main() -> int:
    rows = collect_business_routes()
    failures = []
    failures.extend(check_required_routes(rows))
    failures.extend(check_button_map_references())

    if failures:
        print("Regression gate failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print(f"Regression gate passed: {len(REQUIRED_ROUTES)} critical routes checked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
