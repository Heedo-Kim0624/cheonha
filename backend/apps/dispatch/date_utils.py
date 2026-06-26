from datetime import timedelta

from django.utils.dateparse import parse_date


def _coerce_date(value):
    if not value:
        return None
    if isinstance(value, str):
        return parse_date(value)
    return value


def to_delivery_date(work_date):
    work_date = _coerce_date(work_date)
    return work_date + timedelta(days=1) if work_date else None


def to_work_date(delivery_date):
    delivery_date = _coerce_date(delivery_date)
    return delivery_date - timedelta(days=1) if delivery_date else None


def date_iso(value):
    value = _coerce_date(value)
    return value.isoformat() if value else None
