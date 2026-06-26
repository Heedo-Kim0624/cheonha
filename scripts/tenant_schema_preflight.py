#!/usr/bin/env python
"""Read-only preflight for company tenant schema separation.

This script does not mutate files or databases. It loads the local Django model
registry and prints the first-pass central / dual / tenant classification.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
if str(os.environ.get("DEBUG", "")).lower() not in {
    "",
    "1",
    "0",
    "true",
    "false",
    "yes",
    "no",
    "on",
    "off",
}:
    os.environ["DEBUG"] = "True"


CENTRAL_MODELS = {
    "accounts.CompanyApp",
    "accounts.CompanyTenant",
    "accounts.Shipper",
}

DUAL_MODELS = {
    "accounts.User",
}

CENTRAL_APP_LABELS = {
    "admin",
    "contenttypes",
    "sessions",
}

SHARED_APP_LABELS = {
    "auth",
}

TENANT_APP_LABELS = {
    "accounts",
    "crew",
    "dashboard",
    "dispatch",
    "field_manager",
    "inquiry",
    "manpower",
    "mobile",
    "partner",
    "points",
    "region",
    "settlement",
    "territory",
    "tracking",
    "vehicle_management",
}


@dataclass(frozen=True)
class ModelRow:
    model: str
    table: str
    bucket: str
    reason: str
    relations: tuple[str, ...]


def setup_django():
    import django

    django.setup()


def model_key(model):
    return f"{model._meta.app_label}.{model.__name__}"


def related_model_key(field):
    related = getattr(field, "remote_field", None)
    if not related or not related.model:
        return ""
    model = related.model
    if isinstance(model, str):
        return model
    return model_key(model)


def classify_model(model):
    key = model_key(model)
    app_label = model._meta.app_label
    if key in CENTRAL_MODELS:
        return "central", "global company/shipper registry"
    if key in DUAL_MODELS:
        return "dual", "public central auth plus tenant-local auth"
    if app_label in CENTRAL_APP_LABELS:
        return "central", "django framework metadata in public schema"
    if app_label in SHARED_APP_LABELS:
        return "shared", "django auth metadata, present wherever auth is migrated"
    if app_label in TENANT_APP_LABELS:
        return "tenant", "company operational data"
    return "review", "unclassified app"


def collect_rows():
    from django.apps import apps

    rows = []
    for model in apps.get_models():
        bucket, reason = classify_model(model)
        relations = tuple(
            related
            for field in model._meta.get_fields()
            if field.is_relation
            for related in [related_model_key(field)]
            if related
        )
        rows.append(
            ModelRow(
                model=model_key(model),
                table=model._meta.db_table,
                bucket=bucket,
                reason=reason,
                relations=relations,
            )
        )
    return sorted(rows, key=lambda row: (row.bucket, row.model))


def print_rows(rows):
    print("Tenant schema separation preflight")
    print()
    for bucket in ("central", "dual", "shared", "tenant", "review"):
        bucket_rows = [row for row in rows if row.bucket == bucket]
        print(f"[{bucket}] {len(bucket_rows)} models")
        for row in bucket_rows:
            relations = ", ".join(row.relations) if row.relations else "-"
            print(f"  - {row.model} -> {row.table}")
            print(f"    reason: {row.reason}")
            print(f"    relations: {relations}")
        print()


def print_warnings(rows):
    by_model = {row.model: row for row in rows}
    central = {row.model for row in rows if row.bucket == "central"}
    tenant = {row.model for row in rows if row.bucket == "tenant"}
    dual = {row.model for row in rows if row.bucket == "dual"}

    print("Warnings")
    warnings = []
    for row in rows:
        relation_set = {relation for relation in row.relations if relation in by_model}
        if row.bucket == "tenant" and "." in row.table.replace('"."', "."):
            warnings.append(
                f"tenant model {row.model} uses hard-coded schema table {row.table}; "
                "search_path routing will not move it automatically"
            )
        if row.bucket == "central" and relation_set & tenant:
            warnings.append(
                f"central model {row.model} relates to tenant model(s): {sorted(relation_set & tenant)}"
            )
        if row.bucket == "tenant" and relation_set & central:
            warnings.append(
                f"tenant model {row.model} relates to central model(s): {sorted(relation_set & central)}"
            )
        if row.bucket == "central" and relation_set & dual:
            warnings.append(
                f"central model {row.model} relates to dual model(s): {sorted(relation_set & dual)}; "
                "central queries must stay on public schema"
            )

    if warnings:
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("  - none from first-pass static model inspection")


def main():
    setup_django()
    rows = collect_rows()
    print_rows(rows)
    print_warnings(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
