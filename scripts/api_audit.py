#!/usr/bin/env python
"""Generate a Django REST API inventory and permission audit.

The script intentionally reads the URL resolver instead of parsing source text.
That keeps the output aligned with the endpoints Django actually exposes.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
VALID_DEBUG_VALUES = {"true", "false", "1", "0", "yes", "no", "on", "off"}


def configure_django() -> None:
    sys.path.insert(0, str(BACKEND))
    debug_value = os.environ.get("DEBUG", "True")
    if str(debug_value).lower() not in VALID_DEBUG_VALUES:
        os.environ["DEBUG"] = "True"
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    import django

    django.setup()


@dataclass(frozen=True)
class RouteRow:
    domain: str
    method: str
    path: str
    view: str
    action: str
    permissions: str
    authentication: str
    exposure: str
    helper: bool


def clean_route_pattern(value: str) -> str:
    value = value.replace("^", "").replace("$", "").replace("\\Z", "")
    value = value.replace("\\.", ".")
    value = re.sub(r"\(\?P<format>\[a-z0-9\]\+\)/\?", "{format}", value)
    value = re.sub(r"\(\?P<format>\[a-z0-9\]\+\)", "{format}", value)
    value = re.sub(r"\(\?P<pk>\[\^/\.\]\+\)", "{id}", value)
    value = re.sub(r"\(\?P<pk>\[/\.\]\+\)", "{id}", value)
    value = re.sub(r"\(\?P<(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)>\[\^/\.\]\+\)", r"{\g<name>}", value)
    value = re.sub(r"<int:(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)>", r"{\g<name>}", value)
    value = re.sub(r"<path:(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)>", r"{\g<name>}", value)
    value = value.replace("{pk}", "{id}")
    value = value.replace("{item_id}", "{item_id}")
    return value


def path_domain(path: str) -> str:
    parts = path.strip("/").split("/")
    if len(parts) >= 3 and parts[0] == "api" and parts[1] == "v1":
        return parts[2]
    return parts[0] if parts else ""


def class_names(items: Iterable[object] | None) -> str:
    if items is None:
        return "default"
    items = list(items)
    if not items:
        return "AllowAny"
    names: list[str] = []
    for item in items:
        if isinstance(item, str):
            names.append(item.rsplit(".", 1)[-1])
        elif isinstance(item, type):
            names.append(item.__name__)
        else:
            names.append(item.__class__.__name__)
    return ", ".join(names) if names else "default"


def get_view_identity(callback: object) -> tuple[str, object | None]:
    view_cls = getattr(callback, "cls", None) or getattr(callback, "view_class", None)
    if view_cls:
        return view_cls.__name__, view_cls
    return getattr(callback, "__name__", str(callback)), None


def get_permissions_for_action(view_cls: object | None, action: str) -> str:
    if not view_cls:
        return "default"
    method = getattr(view_cls, action, None)
    method_kwargs = getattr(method, "kwargs", {}) if method else {}
    if "permission_classes" in method_kwargs:
        return class_names(method_kwargs["permission_classes"])
    return class_names(getattr(view_cls, "permission_classes", None))


def get_auth_for_action(view_cls: object | None, action: str) -> str:
    if not view_cls:
        return "default"
    method = getattr(view_cls, action, None)
    method_kwargs = getattr(method, "kwargs", {}) if method else {}
    if "authentication_classes" in method_kwargs:
        return class_names(method_kwargs["authentication_classes"])
    return class_names(getattr(view_cls, "authentication_classes", None))


def classify_exposure(path: str, permissions: str, authentication: str) -> str:
    if "AllowAny" in permissions:
        if path.startswith("api/v1/mobile/"):
            public_mobile = (
                "/app-config/" in path
                or "/register/" in path
                or "/login/" in path
                or "/status/" in path
                or "/refresh/" in path
            )
            return "public" if public_mobile else "custom-mobile-token"
        if path.startswith("api/v1/field-manager/"):
            return "public" if path.endswith("/login/") else "custom-field-manager-token"
        if path.startswith("api/v1/points/"):
            return "custom-mobile-token"
        return "public"
    if "IsAuthenticated" in permissions:
        return "jwt-authenticated"
    if permissions == "default":
        return "default-authenticated"
    if authentication == "default" and permissions == "default":
        return "default-authenticated"
    return "custom"


def is_helper_route(path: str) -> bool:
    if path in {"api/v1/schema/", "api/v1/docs/"}:
        return True
    if "{format}" in path:
        return True
    return bool(
        re.fullmatch(
            r"api/v1/(accounts|crew|dashboard|dispatch|inquiry|manpower|partner|points|region|settlement|territory|tracking|vehicle)/",
            path,
        )
    )


def iter_urlpatterns(patterns, prefix: str = ""):
    from django.urls import URLPattern, URLResolver

    for pattern in patterns:
        raw_pattern = str(pattern.pattern)
        if isinstance(pattern, URLResolver):
            yield from iter_urlpatterns(pattern.url_patterns, prefix + raw_pattern)
        elif isinstance(pattern, URLPattern):
            yield prefix + raw_pattern, pattern.callback


def collect_routes() -> list[RouteRow]:
    from django.urls import get_resolver

    excluded_methods = {"HEAD", "OPTIONS", "TRACE"}
    rows: list[RouteRow] = []

    for raw_path, callback in iter_urlpatterns(get_resolver().url_patterns):
        path = clean_route_pattern(raw_path)
        if not path.startswith("api/v1/"):
            continue

        view_name, view_cls = get_view_identity(callback)
        actions = getattr(callback, "actions", None)

        if actions:
            method_actions = {
                method.upper(): action
                for method, action in actions.items()
                if method.upper() not in excluded_methods
            }
        elif view_cls:
            method_actions = {}
            for method in getattr(view_cls, "http_method_names", []):
                upper = method.upper()
                if upper in excluded_methods:
                    continue
                if hasattr(view_cls, method):
                    method_actions[upper] = method
        else:
            method_actions = {"GET": "function"}

        for method, action in sorted(method_actions.items()):
            permissions = get_permissions_for_action(view_cls, action)
            authentication = get_auth_for_action(view_cls, action)
            helper = is_helper_route(path)
            rows.append(
                RouteRow(
                    domain=path_domain(path),
                    method=method,
                    path=path,
                    view=view_name,
                    action=action,
                    permissions=permissions,
                    authentication=authentication,
                    exposure=classify_exposure(path, permissions, authentication),
                    helper=helper,
                )
            )

    unique: dict[tuple[str, str, str], RouteRow] = {}
    for row in rows:
        unique[(row.method, row.path, row.action)] = row
    return sorted(unique.values(), key=lambda r: (r.path, r.method, r.action))


def business_rows(rows: list[RouteRow]) -> list[RouteRow]:
    return [row for row in rows if not row.helper and "{format}" not in row.path]


def write_csv(rows: list[RouteRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=[
                "domain",
                "method",
                "path",
                "view",
                "action",
                "permissions",
                "authentication",
                "exposure",
                "helper",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def make_markdown(rows: list[RouteRow]) -> str:
    active = business_rows(rows)
    by_domain: dict[str, list[RouteRow]] = defaultdict(list)
    for row in active:
        by_domain[row.domain].append(row)

    exposure_counts = Counter(row.exposure for row in active)
    domain_counts = {
        domain: (len({r.path for r in items}), len(items))
        for domain, items in sorted(by_domain.items())
    }

    duplicate_helpers = [row for row in rows if "{format}" in row.path]
    api_roots = [row for row in rows if row.helper and "{format}" not in row.path]

    lines = [
        "# API 문서화/권한/중복 Endpoint 감사",
        "",
        "이 문서는 `scripts/api_audit.py`가 Django URL resolver를 기준으로 생성한 API 감사 결과입니다.",
        "",
        "## 요약",
        "",
        f"- 업무 API endpoint pattern: **{len({r.path for r in active})}개**",
        f"- 업무 API method-route: **{len(active)}개**",
        f"- 보조 endpoint(schema/docs/router root): **{len({r.path for r in api_roots})}개 path / {len(api_roots)} method-route**",
        f"- DRF format suffix 중복 route: **{len(duplicate_helpers)}개 method-route**",
        "",
        "## 권한 노출 분류",
        "",
        "| 분류 | 개수 | 의미 |",
        "|---|---:|---|",
    ]
    exposure_descriptions = {
        "jwt-authenticated": "일반 관리자 JWT 필요",
        "default-authenticated": "DRF 기본 `IsAuthenticated` 적용",
        "public": "토큰 없이 호출 가능하도록 공개",
        "custom-mobile-token": "`AllowAny`로 열어두고 함수 내부에서 모바일 Bearer token 검사",
        "custom-field-manager-token": "`AllowAny`로 열어두고 함수 내부에서 현장관리자 Bearer token 검사",
        "custom": "커스텀 권한 또는 기타",
    }
    for exposure, count in sorted(exposure_counts.items()):
        lines.append(f"| `{exposure}` | {count} | {exposure_descriptions.get(exposure, '')} |")

    lines.extend(
        [
            "",
            "## 도메인별 규모",
            "",
            "| 도메인 | endpoint pattern | method-route | 주 역할 |",
            "|---|---:|---:|---|",
        ]
    )
    role_map = {
        "accounts": "사용자/팀/가입/토큰",
        "auth": "웹/통합관리 인증",
        "crew": "배송원, 용차, 단가, 연장",
        "dashboard": "KPI, 홈 overview, workflow monitor",
        "dispatch": "배차 업로드, 운영현황, 정산 생성",
        "field-manager": "현장관리자 앱 차량 요청",
        "inquiry": "정산 문의",
        "manpower": "인력풀, 지오코딩, 시트",
        "mobile": "정산 앱 전용 API",
        "partner": "파트너",
        "points": "포인트/상품/교환",
        "region": "지역/단가/단가 이력",
        "settlement": "정산/상세/확정/재계산",
        "territory": "권역 polygon/권역별 박스",
        "tracking": "근무 추적/GPS/CSV",
        "vehicle": "차량/피트/구독/반납/A/S",
    }
    for domain, (path_count, method_count) in domain_counts.items():
        lines.append(f"| `{domain}` | {path_count} | {method_count} | {role_map.get(domain, '')} |")

    lines.extend(
        [
            "",
            "## 중복 Endpoint 판단",
            "",
            "- 실제 업무 중복이라기보다 DRF `DefaultRouter`가 자동 제공하는 `.json` 등 format suffix route가 중복의 대부분입니다.",
            "- `api/v1/<domain>/` router root도 사람이 직접 쓰는 업무 API라기보다 DRF 보조 endpoint입니다.",
            "- 현재 프론트/앱은 대부분 trailing slash 없이도 Nginx/Django가 처리 가능한 경로를 호출하지만, 공식 문서에서는 trailing slash 포함 경로를 표준으로 둡니다.",
            "",
            "## 권한 정리 기준",
            "",
            "- 관리자 웹 API는 기본적으로 `IsAuthenticated`를 유지합니다.",
            "- 모바일 앱 API는 일반 User JWT가 아니라 `crew_member_id` claim을 넣은 별도 토큰을 쓰므로 `custom-mobile-token`으로 분류합니다.",
            "- 현장관리자 앱은 `kind=field_manager` HMAC/JWT를 자체 검증하므로 `custom-field-manager-token`으로 분류합니다.",
            "- 다음 단계에서 코드 정리를 한다면 모바일/현장관리자 토큰 검사를 DRF permission class로 빼서 `AllowAny` 오해를 줄이는 것이 가장 안전한 방향입니다.",
            "",
            "## Endpoint Inventory",
            "",
            "| Domain | Method | Endpoint | Permission | Exposure | View.action |",
            "|---|---|---|---|---|---|",
        ]
    )

    for row in active:
        lines.append(
            f"| `{row.domain}` | `{row.method}` | `{row.path}` | `{row.permissions}` | `{row.exposure}` | `{row.view}.{row.action}` |"
        )

    lines.append("")
    return "\n".join(lines)


def write_markdown(rows: list[RouteRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(make_markdown(rows), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=ROOT / "docs" / "api_inventory.csv")
    parser.add_argument("--markdown", type=Path, default=ROOT / "docs" / "api_audit.md")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    configure_django()
    rows = collect_routes()
    active = business_rows(rows)

    if not args.no_write:
        write_csv(rows, args.csv)
        write_markdown(rows, args.markdown)

    print(f"all method-routes: {len(rows)}")
    print(f"business endpoint patterns: {len({row.path for row in active})}")
    print(f"business method-routes: {len(active)}")
    print("exposure:")
    for exposure, count in sorted(Counter(row.exposure for row in active).items()):
        print(f"  {exposure}: {count}")
    if not args.no_write:
        print(f"wrote: {args.csv}")
        print(f"wrote: {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
