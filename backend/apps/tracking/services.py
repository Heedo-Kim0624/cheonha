import csv
import io
import json
import logging
import math
import os
import re
import threading
from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache
from typing import Iterable

import numpy as np
import pandas as pd
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import close_old_connections, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.crew.models import CrewMember
from apps.tracking.algorithms.ble_state import classify_three_states
from apps.tracking.algorithms.kalman import smooth_gps_track
from apps.tracking.models import (
    STATE_DELIVERING,
    STATE_IN_VEHICLE,
    STATE_SEARCHING,
    BleLog,
    CameraCapture,
    Cycle,
    LiveWorkSessionStatus,
    LocationPoint,
    TrackingSession,
)


CSV_HEADER_ALIASES = {
    "timestamp": ["시간", "timestamp", "time", "recorded_at"],
    "name": ["이름", "name"],
    "rssi": ["rssi"],
    "barometer": ["barometer", "pressure_hpa", "pressure"],
    "latitude": ["위도", "latitude", "lat"],
    "longitude": ["경도", "longitude", "lon"],
    "speed_kmh": ["속도_kmh", "speed_kmh"],
    "accuracy_m": ["정확도_m", "accuracy_m"],
    "camera_start": ["camera_start"],
    "camera_end": ["camera_end"],
    "camera_captured": ["camera_captured"],
}

RAW_TRACKING_CSV_DIR = "tracking/work_sessions"
PROCESSED_TRACKING_CSV_EXPORT_DIR_ENV = "TRACKING_PROCESSED_CSV_EXPORT_DIR"
TRACKING_DRIVE_FOLDER_ID_ENV = "TRACKING_DRIVE_FOLDER_ID"
TRACKING_DRIVE_SERVICE_ACCOUNT_FILE_ENV = "TRACKING_DRIVE_SERVICE_ACCOUNT_FILE"
GOOGLE_APPLICATION_CREDENTIALS_ENV = "GOOGLE_APPLICATION_CREDENTIALS"
DEFAULT_TRACKING_DRIVE_FOLDER_ID = "1vwetxc_7enBXyzn3xiGYVWWN_zi5S0pL"
GOOGLE_DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
TRACKING_DRIVE_MIN_VERSION_CODE_ENV = "TRACKING_DRIVE_MIN_VERSION_CODE"
TRACKING_DRIVE_MASK_START_DATE_ENV = "TRACKING_DRIVE_MASK_START_DATE"
TRACKING_DRIVE_REQUIRE_MARKETING_CONSENT_ENV = "TRACKING_DRIVE_REQUIRE_MARKETING_CONSENT"
TRACKING_DRIVE_INCLUDE_WEATHER_ENV = "TRACKING_DRIVE_INCLUDE_WEATHER"
TRACKING_AWS_ZONES_FILE_ENV = "TRACKING_AWS_ZONES_FILE"
TRACKING_AWS_WEATHER_FILE_ENV = "TRACKING_AWS_WEATHER_FILE"
DEFAULT_TRACKING_DRIVE_MIN_VERSION_CODE = 47
DEFAULT_TRACKING_DRIVE_MASK_START_DATE = "2000-01-01"
DEFAULT_TRACKING_AWS_ZONES_FILE = os.path.join(
    os.path.dirname(__file__),
    "data",
    "aws_zones.json",
)
DEFAULT_TRACKING_AWS_WEATHER_FILE = os.path.join(
    os.path.dirname(__file__),
    "data",
    "aws_weather_hourly.csv",
)
logger = logging.getLogger(__name__)


@dataclass
class ParsedSample:
    recorded_at: timezone.datetime
    rssi: int | None
    barometer: float | None
    lat: float | None
    lon: float | None
    speed_kmh: float | None
    accuracy_m: float | None
    camera_start: int
    camera_end: int
    camera_captured: int


@dataclass
class MobileTrackingUploadSummary:
    samples: list[ParsedSample]
    session_date: timezone.datetime.date
    started_at: timezone.datetime
    ended_at: timezone.datetime
    total_seconds: int
    bbox_min_lat: float | None
    bbox_min_lon: float | None
    bbox_max_lat: float | None
    bbox_max_lon: float | None
    has_rssi: bool
    camera_end_count: int
    source_name: str


class MobileTrackingUploadError(ValueError):
    pass


def mark_live_work_session_started(
    *,
    crew: CrewMember,
    vehicle_number: str = "",
    background_location_granted: bool = False,
    started_at=None,
    app_version: str = "",
):
    timestamp = started_at or timezone.now()
    normalized_vehicle = str(vehicle_number or crew.vehicle_number or "").strip()
    normalized_app_version = str(app_version or "").strip()[:40]
    defaults = {
        "status": LiveWorkSessionStatus.Status.RUNNING,
        "current_vehicle_number": normalized_vehicle,
        "session_started_at": timestamp,
        "session_ended_at": None,
        "last_seen_at": timestamp,
        "background_location_granted": bool(background_location_granted),
    }
    if normalized_app_version:
        defaults["last_app_version"] = normalized_app_version
    status, _ = LiveWorkSessionStatus.objects.update_or_create(
        crew_member=crew,
        defaults=defaults,
    )
    return status


def heartbeat_live_work_session(
    *,
    crew: CrewMember,
    vehicle_number: str = "",
    background_location_granted: bool | None = None,
    seen_at=None,
    app_version: str = "",
):
    timestamp = seen_at or timezone.now()
    defaults = {
        "status": LiveWorkSessionStatus.Status.RUNNING,
        "last_seen_at": timestamp,
    }
    normalized_vehicle = str(vehicle_number or "").strip()
    if normalized_vehicle:
        defaults["current_vehicle_number"] = normalized_vehicle
    if background_location_granted is not None:
        defaults["background_location_granted"] = bool(background_location_granted)
    normalized_app_version = str(app_version or "").strip()[:40]
    if normalized_app_version:
        defaults["last_app_version"] = normalized_app_version

    status, _ = LiveWorkSessionStatus.objects.update_or_create(
        crew_member=crew,
        defaults=defaults,
    )
    return status


def mark_live_work_session_stopped(
    *,
    crew: CrewMember,
    vehicle_number: str = "",
    background_location_granted: bool | None = None,
    ended_at=None,
    app_version: str = "",
):
    timestamp = ended_at or timezone.now()
    normalized_app_version = str(app_version or "").strip()[:40]
    status, _ = LiveWorkSessionStatus.objects.update_or_create(
        crew_member=crew,
        defaults={
            "status": LiveWorkSessionStatus.Status.STOPPED,
            "current_vehicle_number": str(vehicle_number or crew.vehicle_number or "").strip(),
            "session_ended_at": timestamp,
            "last_seen_at": timestamp,
            **({"last_app_version": normalized_app_version} if normalized_app_version else {}),
            **(
                {"background_location_granted": bool(background_location_granted)}
                if background_location_granted is not None
                else {}
            ),
        },
    )
    return status


def raw_tracking_csv_path(session_id: int) -> str:
    return f"{RAW_TRACKING_CSV_DIR}/session_{session_id}.csv"


def save_raw_tracking_csv(session: TrackingSession, csv_content: str) -> str:
    """Persist the exact uploaded mobile CSV at a deterministic media path."""
    path = raw_tracking_csv_path(session.id)
    if default_storage.exists(path):
        default_storage.delete(path)
    default_storage.save(path, ContentFile(str(csv_content or "").encode("utf-8")))
    return path


def summarize_mobile_tracking_upload(
    *,
    csv_content: str,
    source_name: str = "",
) -> MobileTrackingUploadSummary:
    samples = _parse_samples(csv_content)
    gps_samples = [sample for sample in samples if sample.lat is not None and sample.lon is not None]
    if not gps_samples:
        raise MobileTrackingUploadError("GPS 위치 데이터가 없어 배송 추적을 생성할 수 없습니다.")

    has_camera_end_events = any(sample.camera_end for sample in samples)
    camera_end_count = sum(
        1
        for sample in samples
        if sample.camera_end or (not has_camera_end_events and sample.camera_captured)
    )

    return MobileTrackingUploadSummary(
        samples=samples,
        session_date=samples[0].recorded_at.date(),
        started_at=samples[0].recorded_at,
        ended_at=samples[-1].recorded_at,
        total_seconds=max(0, int((samples[-1].recorded_at - samples[0].recorded_at).total_seconds())),
        bbox_min_lat=min(sample.lat for sample in gps_samples if sample.lat is not None),
        bbox_min_lon=min(sample.lon for sample in gps_samples if sample.lon is not None),
        bbox_max_lat=max(sample.lat for sample in gps_samples if sample.lat is not None),
        bbox_max_lon=max(sample.lon for sample in gps_samples if sample.lon is not None),
        has_rssi=any(sample.rssi is not None for sample in samples),
        camera_end_count=camera_end_count,
        source_name=(source_name or "MOBILE").strip()[:64],
    )


def get_or_create_tracking_session_stub(
    *,
    crew: CrewMember,
    summary: MobileTrackingUploadSummary,
    vehicle_number: str = "",
    app_version: str = "",
) -> tuple[TrackingSession, bool]:
    if vehicle_number and crew.vehicle_number != vehicle_number:
        crew.vehicle_number = vehicle_number
        crew.save(update_fields=["vehicle_number", "updated_at"])

    normalized_app_version = str(app_version or "").strip()[:40]
    defaults = {
        "session_date": summary.session_date,
        "started_at": summary.started_at,
        "ended_at": summary.ended_at,
        "device_id": summary.source_name,
        "total_seconds": summary.total_seconds,
        "iv_seconds": 0,
        "sr_seconds": 0,
        "dl_seconds": 0,
        "distance_m": 0,
        "cycle_count": 0,
        "bbox_min_lat": summary.bbox_min_lat,
        "bbox_min_lon": summary.bbox_min_lon,
        "bbox_max_lat": summary.bbox_max_lat,
        "bbox_max_lon": summary.bbox_max_lon,
    }
    if normalized_app_version:
        defaults["app_version"] = normalized_app_version

    session = (
        TrackingSession.objects.filter(
            crew_member=crew,
            started_at=summary.started_at,
            ended_at=summary.ended_at,
            device_id=summary.source_name,
        )
        .order_by("-created_at")
        .first()
    )
    if session:
        changed_fields = []
        for field_name, value in defaults.items():
            if getattr(session, field_name) != value:
                setattr(session, field_name, value)
                changed_fields.append(field_name)
        if changed_fields:
            changed_fields.append("updated_at")
            session.save(update_fields=changed_fields)
        return session, False

    session = TrackingSession.objects.create(
        crew_member=crew,
        **defaults,
    )
    return session, True


def _local_second(value):
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.replace(microsecond=0)


def _format_csv_time(value) -> str:
    return _local_second(value).strftime("%Y-%m-%d %H:%M:%S")


def _format_csv_float(value, digits: int = 6) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return ""


def build_tracking_session_csv(session: TrackingSession) -> str:
    """
    Rebuild a downloadable CSV from stored tracking tables.

    Existing sessions created before raw CSV persistence will not have barometer
    samples or camera-only open/close events, because those were not persisted.
    """
    rows: dict[object, dict[str, object]] = {}
    crew_name = session.crew_member.name if session.crew_member else ""
    cycle_no_by_id = {
        cycle.id: cycle.cycle_no
        for cycle in session.cycles.all().only("id", "cycle_no")
    }

    def ensure_row(recorded_at):
        key = _local_second(recorded_at)
        row = rows.get(key)
        if row is None:
            row = {
                "time": _format_csv_time(recorded_at),
                "name": crew_name,
                "rssi": "",
                "barometer": "",
                "lat": "",
                "lon": "",
                "speed_kmh": "",
                "accuracy_m": "",
                "state": "",
                "cycle_no": "",
                "camera_start": 0,
                "camera_end": 0,
                "camera_captured": 0,
                "camera_duration_ms": "",
            }
            rows[key] = row
        return row

    for point in session.points.all().order_by("recorded_at"):
        row = ensure_row(point.recorded_at)
        row["lat"] = _format_csv_float(point.lat, 6)
        row["lon"] = _format_csv_float(point.lon, 6)
        row["speed_kmh"] = _format_csv_float(point.speed_kmh, 2)
        row["accuracy_m"] = _format_csv_float(point.accuracy_m, 2)
        row["state"] = point.state or ""
        if point.cycle_id:
            row["cycle_no"] = cycle_no_by_id.get(point.cycle_id, "")

    for ble in session.ble_logs.all().order_by("recorded_at"):
        row = ensure_row(ble.recorded_at)
        if ble.rssi is not None:
            row["rssi"] = ble.rssi

    for capture in session.captures.all().order_by("captured_at"):
        if capture.started_at:
            started_row = ensure_row(capture.started_at)
            started_row["camera_start"] = 1
        captured_row = ensure_row(capture.captured_at)
        captured_row["camera_end"] = 1
        captured_row["camera_captured"] = 1
        captured_row["camera_duration_ms"] = capture.duration_ms
        if capture.lat is not None:
            captured_row["lat"] = _format_csv_float(capture.lat, 6)
        if capture.lon is not None:
            captured_row["lon"] = _format_csv_float(capture.lon, 6)
        if capture.cycle_id:
            captured_row["cycle_no"] = cycle_no_by_id.get(capture.cycle_id, "")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "시간",
        "이름",
        "rssi",
        "barometer",
        "위도",
        "경도",
        "속도_kmh",
        "정확도_m",
        "state",
        "cycle_no",
        "camera_start",
        "camera_end",
        "camera_captured",
        "camera_duration_ms",
    ])
    for key in sorted(rows):
        row = rows[key]
        writer.writerow([
            row["time"],
            row["name"],
            row["rssi"],
            row["barometer"],
            row["lat"],
            row["lon"],
            row["speed_kmh"],
            row["accuracy_m"],
            row["state"],
            row["cycle_no"],
            row["camera_start"],
            row["camera_end"],
            row["camera_captured"],
            row["camera_duration_ms"],
        ])
    return output.getvalue()


def _truthy_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_mobile_app_version(value: object) -> tuple[tuple[int, int, int], int]:
    text = str(value or "").strip()
    if not text:
        return (0, 0, 0), 0

    version_code = 0
    code_match = re.search(r"\((\d+)\)\s*$", text)
    if not code_match:
        code_match = re.search(r"(?:versionCode|vc|vcode)[\s:_-]*(\d+)", text, re.IGNORECASE)
    if code_match:
        version_code = int(code_match.group(1))
    elif text.isdigit():
        version_code = int(text)

    semver = (0, 0, 0)
    semver_match = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    if semver_match:
        semver = tuple(int(part) for part in semver_match.groups())

    return semver, version_code


def _is_supported_tracking_drive_app_version(value: object) -> bool:
    min_code = int(os.environ.get(TRACKING_DRIVE_MIN_VERSION_CODE_ENV, DEFAULT_TRACKING_DRIVE_MIN_VERSION_CODE) or 0)
    semver, version_code = _parse_mobile_app_version(value)
    if min_code > 0 and version_code >= min_code:
        return True
    return semver >= (1, 0, 45)


def _mobile_user_has_tracking_drive_export_consents(mobile_user) -> bool:
    if not mobile_user:
        return False
    if not getattr(mobile_user, "is_active", False):
        return False
    if getattr(mobile_user, "status", "") != "APPROVED":
        return False
    if not getattr(mobile_user, "signup_completed", False):
        return False
    required_fields = [
        "privacy_policy_agreed_at",
        "terms_agreed_at",
        "third_party_information_agreed_at",
        "location_terms_agreed_at",
    ]
    if _truthy_env(TRACKING_DRIVE_REQUIRE_MARKETING_CONSENT_ENV, False):
        required_fields.append("marketing_event_agreed_at")
    return all(bool(getattr(mobile_user, field, None)) for field in required_fields)


def _session_is_allowed_for_tracking_drive_export(session: TrackingSession) -> bool:
    crew = getattr(session, "crew_member", None)
    mobile_user = getattr(crew, "mobile_app_user", None) if crew else None
    return (
        _mobile_user_has_tracking_drive_export_consents(mobile_user)
        and _is_supported_tracking_drive_app_version(getattr(session, "app_version", ""))
    )


def _anonymized_crew_export_code(crew: CrewMember | None) -> str:
    if not crew:
        return "UNK-000"
    team = getattr(crew, "team", None)
    team_code = _safe_export_filename_part(getattr(team, "code", "") or "UNK", "UNK").upper()
    if not getattr(crew, "team_id", None) or not getattr(crew, "id", None):
        return f"{team_code}-000"
    sequence = CrewMember.objects.filter(team_id=crew.team_id, id__lte=crew.id).order_by().count()
    return f"{team_code}-{max(1, sequence):03d}"


def _tracking_drive_mask_base_datetime():
    raw_date = os.environ.get(TRACKING_DRIVE_MASK_START_DATE_ENV, DEFAULT_TRACKING_DRIVE_MASK_START_DATE)
    try:
        base_date = timezone.datetime.strptime(str(raw_date or "").strip(), "%Y-%m-%d")
    except ValueError:
        base_date = timezone.datetime(2000, 1, 1)
    return timezone.make_aware(base_date, timezone.get_current_timezone())


def _csv_field_lookup(fieldnames: list[str], aliases: Iterable[str]) -> str | None:
    normalized = {str(name or "").strip().lower(): name for name in fieldnames}
    for alias in aliases:
        match = normalized.get(str(alias or "").strip().lower())
        if match is not None:
            return match
    return None


def _nearest_ble_state(state_series, recorded_at) -> str:
    if state_series is None or state_series.empty or recorded_at is None:
        return ""
    try:
        idx = state_series.index.get_indexer([recorded_at], method="nearest")[0]
    except Exception:
        return ""
    if idx < 0:
        return ""
    return str(state_series.iloc[idx].get("state") or "")


WEATHER_EXPORT_FIELDS = [
    "time_band",
    "aws_station_id",
    "aws_station_name",
    "temp_c",
    "wind_dir_deg",
    "wind_speed_ms",
    "precip_mm",
    "local_pressure_hpa",
    "sea_level_pressure_hpa",
    "humidity_pct",
]


def _weather_source_paths() -> tuple[str, str]:
    return (
        os.environ.get(TRACKING_AWS_ZONES_FILE_ENV, DEFAULT_TRACKING_AWS_ZONES_FILE),
        os.environ.get(TRACKING_AWS_WEATHER_FILE_ENV, DEFAULT_TRACKING_AWS_WEATHER_FILE),
    )


@lru_cache(maxsize=1)
def _load_aws_zones_for_export() -> list[dict]:
    zones_path, _ = _weather_source_paths()
    if not zones_path or not os.path.exists(zones_path):
        return []
    with open(zones_path, "r", encoding="utf-8") as source:
        payload = json.load(source)
    return list(payload.get("zones") or [])


@lru_cache(maxsize=1)
def _load_aws_weather_for_export() -> dict[tuple[int, str], dict[str, str]]:
    _, weather_path = _weather_source_paths()
    if not weather_path or not os.path.exists(weather_path):
        return {}
    weather_rows: dict[tuple[int, str], dict[str, str]] = {}
    with open(weather_path, "r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        for row in reader:
            try:
                station_id = int(float(str(row.get("station_id") or "").strip()))
            except (TypeError, ValueError):
                continue
            observed_at = str(row.get("observed_at") or "").strip()
            if not observed_at:
                continue
            weather_rows[(station_id, observed_at)] = {
                "aws_station_id": str(station_id),
                "aws_station_name": str(row.get("station_name") or "").strip(),
                "temp_c": str(row.get("temp_c") or "").strip(),
                "wind_dir_deg": str(row.get("wind_dir_deg") or "").strip(),
                "wind_speed_ms": str(row.get("wind_speed_ms") or "").strip(),
                "precip_mm": str(row.get("precip_mm") or "").strip(),
                "local_pressure_hpa": str(row.get("local_pressure_hpa") or "").strip(),
                "sea_level_pressure_hpa": str(row.get("sea_level_pressure_hpa") or "").strip(),
                "humidity_pct": str(row.get("humidity_pct") or "").strip(),
            }
    return weather_rows


def _point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    inside = False
    if len(ring) < 3:
        return False
    j = len(ring) - 1
    for i, point in enumerate(ring):
        xi, yi = point[0], point[1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat):
            x_intersect = (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi
            if lon < x_intersect:
                inside = not inside
        j = i
    return inside


def _point_in_zone(lon: float, lat: float, zone: dict) -> bool:
    min_lon, min_lat, max_lon, max_lat = zone.get("bbox") or [None, None, None, None]
    if (
        min_lon is None
        or lon < float(min_lon)
        or lon > float(max_lon)
        or lat < float(min_lat)
        or lat > float(max_lat)
    ):
        return False
    for polygon in zone.get("polygons") or []:
        if not polygon or not _point_in_ring(lon, lat, polygon[0]):
            continue
        if any(_point_in_ring(lon, lat, hole) for hole in polygon[1:]):
            continue
        return True
    return False


def _find_aws_zone_for_point(lon: float, lat: float) -> dict | None:
    for zone in _load_aws_zones_for_export():
        if _point_in_zone(lon, lat, zone):
            return zone
    return None


def _weather_hour_key(recorded_at) -> str:
    local_dt = timezone.localtime(recorded_at)
    return local_dt.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")


def _time_band_for_recorded_at(recorded_at) -> str:
    local_dt = timezone.localtime(recorded_at)
    return f"D{(local_dt.hour // 2) + 1}"


def _weather_export_values(recorded_at, lat_raw: str, lon_raw: str) -> dict[str, str]:
    values = {field: "" for field in WEATHER_EXPORT_FIELDS}
    if recorded_at is None:
        return values
    values["time_band"] = _time_band_for_recorded_at(recorded_at)
    try:
        lat = float(str(lat_raw or "").strip())
        lon = float(str(lon_raw or "").strip())
    except (TypeError, ValueError):
        return values

    zone = _find_aws_zone_for_point(lon, lat)
    if not zone:
        return values
    station_id = int(zone["station_id"])
    weather = _load_aws_weather_for_export().get((station_id, _weather_hour_key(recorded_at)))
    values["aws_station_id"] = str(station_id)
    values["aws_station_name"] = str(zone.get("station_name") or "")
    if weather:
        values.update(weather)
    return values


def _build_privacy_preserving_tracking_drive_csv(
    *,
    session: TrackingSession,
    raw_csv_content: str,
) -> str:
    raw_csv_content = str(raw_csv_content or "").lstrip("\ufeff")
    source = io.StringIO(raw_csv_content)
    reader = csv.DictReader(source)
    fieldnames = list(reader.fieldnames or [])
    rows = list(reader)
    if not fieldnames:
        return build_tracking_session_csv(session)

    timestamp_field = _csv_field_lookup(
        fieldnames,
        [*CSV_HEADER_ALIASES["timestamp"], "시간", "시각", "일시"],
    )
    name_field = _csv_field_lookup(
        fieldnames,
        [*CSV_HEADER_ALIASES["name"], "이름", "배송원", "기사명"],
    )
    latitude_field = _csv_field_lookup(
        fieldnames,
        [*CSV_HEADER_ALIASES["latitude"], "위도", "latitude", "lat"],
    )
    longitude_field = _csv_field_lookup(
        fieldnames,
        [*CSV_HEADER_ALIASES["longitude"], "경도", "longitude", "lon", "lng"],
    )
    anonymized_code = _anonymized_crew_export_code(session.crew_member)
    original_names = {
        str(getattr(session.crew_member, "name", "") or "").strip(),
        str(getattr(session.crew_member, "code", "") or "").strip(),
    }
    original_names.discard("")

    parsed_times: list[timezone.datetime | None] = []
    first_time = None
    for row in rows:
        recorded_at = None
        if timestamp_field:
            try:
                recorded_at = _parse_datetime_value(row.get(timestamp_field, ""))
            except Exception:
                recorded_at = None
        parsed_times.append(recorded_at)
        if recorded_at is not None and (first_time is None or recorded_at < first_time):
            first_time = recorded_at

    first_time = first_time or _local_second(session.started_at)
    masked_start = _tracking_drive_mask_base_datetime()

    state_series = None
    try:
        samples = _parse_samples(raw_csv_content)
        ble_df = pd.DataFrame(
            [
                {"time": sample.recorded_at, "rssi": sample.rssi}
                for sample in samples
                if sample.rssi is not None
            ]
        )
        if not ble_df.empty:
            state_series = classify_three_states(ble_df[["time", "rssi"]])
    except Exception:
        state_series = None

    output_fieldnames = list(fieldnames)
    state_field = "state"
    if state_field not in output_fieldnames:
        output_fieldnames.append(state_field)
    include_weather = _truthy_env(TRACKING_DRIVE_INCLUDE_WEATHER_ENV, False)
    if include_weather:
        for field_name in WEATHER_EXPORT_FIELDS:
            if field_name not in output_fieldnames:
                output_fieldnames.append(field_name)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=output_fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row, recorded_at in zip(rows, parsed_times):
        exported_row = dict(row)
        if include_weather:
            exported_row.update(
                _weather_export_values(
                    recorded_at,
                    row.get(latitude_field, "") if latitude_field else "",
                    row.get(longitude_field, "") if longitude_field else "",
                )
            )
        if timestamp_field and recorded_at is not None:
            masked_time = masked_start + (recorded_at - first_time)
            exported_row[timestamp_field] = _format_csv_time(masked_time)
        if name_field:
            exported_row[name_field] = anonymized_code
        for field_name, value in list(exported_row.items()):
            if str(value or "").strip() in original_names:
                exported_row[field_name] = anonymized_code
        exported_row[state_field] = _nearest_ble_state(state_series, recorded_at)
        writer.writerow(exported_row)
    return output.getvalue()


def _load_raw_tracking_csv(session: TrackingSession) -> str | None:
    path = raw_tracking_csv_path(session.id)
    if not default_storage.exists(path):
        return None
    with default_storage.open(path, "rb") as raw_file:
        return raw_file.read().decode("utf-8-sig")


def _safe_export_filename_part(value: object, fallback: str = "unknown") -> str:
    text = str(value or "").strip()
    if not text:
        text = fallback
    text = re.sub(r'[\\/:*?"<>|\s]+', "_", text)
    text = re.sub(r"_+", "_", text).strip("._")
    return (text or fallback)[:80]


def _tracking_drive_folder_id() -> str:
    return os.environ.get(TRACKING_DRIVE_FOLDER_ID_ENV, DEFAULT_TRACKING_DRIVE_FOLDER_ID).strip()


def _tracking_drive_credentials_path() -> str:
    return (
        os.environ.get(TRACKING_DRIVE_SERVICE_ACCOUNT_FILE_ENV)
        or os.environ.get(GOOGLE_APPLICATION_CREDENTIALS_ENV)
        or ""
    ).strip()


def _upload_csv_to_google_drive(filename: str, csv_content: str) -> str | None:
    folder_id = _tracking_drive_folder_id()
    credentials_path = _tracking_drive_credentials_path()
    if not folder_id or not credentials_path:
        return None
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"Google Drive service account file not found: {credentials_path}")

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload
    except ImportError as exc:
        raise RuntimeError(
            "Google Drive upload requires google-api-python-client and google-auth packages."
        ) from exc

    credentials = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=[GOOGLE_DRIVE_FILE_SCOPE],
    )
    service = build("drive", "v3", credentials=credentials, cache_discovery=False)
    media = MediaIoBaseUpload(
        io.BytesIO(csv_content.encode("utf-8-sig")),
        mimetype="text/csv",
        resumable=True,
    )
    uploaded = service.files().create(
        body={"name": filename, "parents": [folder_id]},
        media_body=media,
        fields="id, webViewLink",
        supportsAllDrives=True,
    ).execute()
    return uploaded.get("webViewLink") or f"drive:{uploaded.get('id')}"


def export_processed_tracking_csv(
    session: TrackingSession,
    export_dir: str | None = None,
    raw_csv_content: str | None = None,
) -> str | None:
    """
    Save/upload the BLE/GPS processed tracking CSV after mobile work upload.

    Local folder export is enabled by TRACKING_PROCESSED_CSV_EXPORT_DIR.
    Google Drive upload is enabled when a service account credentials file is
    configured. TRACKING_DRIVE_FOLDER_ID defaults to the operations folder.
    """
    target_dir = (
        export_dir
        if export_dir is not None
        else os.environ.get(PROCESSED_TRACKING_CSV_EXPORT_DIR_ENV, "")
    )
    target_dir = str(target_dir or "").strip()
    should_upload_drive = bool(_tracking_drive_credentials_path())
    if not target_dir and not should_upload_drive:
        return None

    loaded_session = (
        TrackingSession.objects
        .select_related("crew_member", "crew_member__team", "crew_member__mobile_app_user")
        .prefetch_related("points", "ble_logs", "captures", "cycles")
        .get(pk=session.pk)
    )
    if not _session_is_allowed_for_tracking_drive_export(loaded_session):
        return None

    anonymized_code = _anonymized_crew_export_code(loaded_session.crew_member)
    filename = "_".join([
        "tracking",
        f"session{loaded_session.pk}",
        _safe_export_filename_part(anonymized_code, "crew"),
    ]) + ".csv"
    source_csv = raw_csv_content if raw_csv_content is not None else _load_raw_tracking_csv(loaded_session)
    if not source_csv:
        return None
    csv_content = _build_privacy_preserving_tracking_drive_csv(
        session=loaded_session,
        raw_csv_content=source_csv,
    )

    exported_targets: list[str] = []
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)
        output_path = os.path.join(target_dir, filename)
        with open(output_path, "w", encoding="utf-8-sig", newline="") as output:
            output.write(csv_content)
        exported_targets.append(output_path)

    if should_upload_drive:
        drive_target = _upload_csv_to_google_drive(filename, csv_content)
        if drive_target:
            exported_targets.append(drive_target)

    return ", ".join(exported_targets) if exported_targets else None


def _get_first_value(row: dict[str, str], names: Iterable[str]) -> str:
    for name in names:
        if name in row:
            return str(row.get(name) or "").strip()
    return ""


def _parse_datetime_value(raw: str):
    value = str(raw or "").strip()
    if not value:
        raise MobileTrackingUploadError("시간 값이 비어 있습니다.")
    dt = parse_datetime(value)
    if dt is None:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
            try:
                dt = timezone.datetime.strptime(value, fmt)
                break
            except ValueError:
                continue
    if dt is None:
        raise MobileTrackingUploadError(f"시간 형식을 해석할 수 없습니다: {value}")
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt.astimezone(timezone.get_current_timezone())


def _parse_float(value: str) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _parse_int(value: str) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _parse_flag(value: str) -> int:
    parsed = _parse_int(value)
    return 1 if parsed else 0


def _parse_samples(csv_content: str) -> list[ParsedSample]:
    source = io.StringIO((csv_content or "").lstrip("\ufeff"))
    reader = csv.DictReader(source)
    rows: list[ParsedSample] = []
    for row in reader:
        recorded_at = _parse_datetime_value(
            _get_first_value(row, CSV_HEADER_ALIASES["timestamp"])
        )
        rows.append(
            ParsedSample(
                recorded_at=recorded_at,
                rssi=_parse_int(_get_first_value(row, CSV_HEADER_ALIASES["rssi"])),
                barometer=_parse_float(
                    _get_first_value(row, CSV_HEADER_ALIASES["barometer"])
                ),
                lat=_parse_float(_get_first_value(row, CSV_HEADER_ALIASES["latitude"])),
                lon=_parse_float(_get_first_value(row, CSV_HEADER_ALIASES["longitude"])),
                speed_kmh=_parse_float(
                    _get_first_value(row, CSV_HEADER_ALIASES["speed_kmh"])
                ),
                accuracy_m=_parse_float(
                    _get_first_value(row, CSV_HEADER_ALIASES["accuracy_m"])
                ),
                camera_start=_parse_flag(
                    _get_first_value(row, CSV_HEADER_ALIASES["camera_start"])
                ),
                camera_end=_parse_flag(
                    _get_first_value(row, CSV_HEADER_ALIASES["camera_end"])
                ),
                camera_captured=_parse_flag(
                    _get_first_value(row, CSV_HEADER_ALIASES["camera_captured"])
                ),
            )
        )
    rows.sort(key=lambda item: item.recorded_at)
    if not rows:
        raise MobileTrackingUploadError("업로드할 근무 기록이 없습니다.")
    return rows


def _extract_capture_events(samples: list[ParsedSample]) -> list[dict]:
    current_camera_started_at = None
    current_camera_session_has_capture = False
    capture_events = []

    for sample in samples:
        if sample.camera_start:
            current_camera_started_at = sample.recorded_at
            current_camera_session_has_capture = False

        if sample.camera_captured:
            capture_events.append(
                {
                    "started_at": (
                        current_camera_started_at
                        if not current_camera_session_has_capture
                        else None
                    ),
                    "captured_at": sample.recorded_at,
                }
            )
            current_camera_session_has_capture = True
        elif sample.camera_end and not current_camera_session_has_capture:
            capture_events.append(
                {
                    "started_at": current_camera_started_at,
                    "captured_at": sample.recorded_at,
                }
            )

        if sample.camera_end:
            current_camera_started_at = None
            current_camera_session_has_capture = False

    return capture_events


def _extract_capture_times(samples: list[ParsedSample]) -> list[timezone.datetime]:
    return [event["captured_at"] for event in _extract_capture_events(samples)]


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_r = 6378137.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * earth_r * math.asin(math.sqrt(max(0.0, min(1.0, a))))


def _smooth_gps(gps_df: pd.DataFrame) -> pd.DataFrame:
    if gps_df.empty:
        return gps_df

    out = gps_df.copy()
    out["lat_f"] = out["lat"]
    out["lon_f"] = out["lon"]
    if len(out) < 2:
        return out

    t_sec = (
        pd.to_datetime(out["time"], utc=False).astype("int64") // 10**9
    ).to_numpy()
    accuracy = out["accuracy_m"].fillna(10.0).to_numpy(dtype=float)
    speed = out["speed_kmh"].fillna(0.0).to_numpy(dtype=float)

    try:
        filtered_lat, filtered_lon = smooth_gps_track(
            out["lat"].to_numpy(dtype=float),
            out["lon"].to_numpy(dtype=float),
            t_sec,
            accuracy_m=accuracy,
            speed_kmh=speed,
        )
        mask = np.isfinite(filtered_lat) & np.isfinite(filtered_lon)
        out.loc[mask, "lat_f"] = filtered_lat[mask]
        out.loc[mask, "lon_f"] = filtered_lon[mask]
    except Exception:
        pass

    return out


def _resolve_state(ts, speed_kmh, capture_times, state_series):
    if state_series is not None and not state_series.empty:
        idx = state_series.index.get_indexer([ts], method="nearest")[0]
        row = state_series.iloc[idx]
        state = {
            "IV": STATE_IN_VEHICLE,
            "SR": STATE_SEARCHING,
            "DL": STATE_DELIVERING,
        }.get(row["state"], STATE_IN_VEHICLE)
        raw_cycle_id = int(row["cycle_id"] or 0) or None
        return state, raw_cycle_id

    near_capture = any(abs((ts - item).total_seconds()) <= 60 for item in capture_times)
    if (speed_kmh or 0) > 10:
        return STATE_IN_VEHICLE, None
    if near_capture:
        return STATE_DELIVERING, 1
    return STATE_SEARCHING, 1


def _build_cycle_specs(gps_records: list[dict]) -> list[dict]:
    cycles = []
    current = None
    last_cycle_id = 0

    for record in gps_records:
        if record["state"] == STATE_IN_VEHICLE:
            if current:
                cycles.append(current)
                current = None
            continue

        raw_cycle_id = record["raw_cycle_id"] or (last_cycle_id + 1)
        if current is None or current["raw_cycle_id"] != raw_cycle_id:
            if current:
                cycles.append(current)
            last_cycle_id = raw_cycle_id
            current = {
                "raw_cycle_id": raw_cycle_id,
                "start": record["recorded_at"],
                "end": record["recorded_at"],
                "records": [record],
            }
        else:
            current["end"] = record["recorded_at"]
            current["records"].append(record)

    if current:
        cycles.append(current)

    cycle_specs = []
    cycle_no = 0
    for cycle in cycles:
        records = cycle["records"]
        duration = (cycle["end"] - cycle["start"]).total_seconds()
        if duration < 15 or len(records) < 5:
            continue

        cycle_no += 1
        distance_m = 0.0
        for index in range(1, len(records)):
            prev = records[index - 1]
            cur = records[index]
            distance_m += _haversine_m(prev["lat"], prev["lon"], cur["lat"], cur["lon"])

        speed_values = [item["speed_kmh"] for item in records if item["speed_kmh"] is not None]
        accuracy_values = [
            item["accuracy_m"] for item in records if item["accuracy_m"] is not None
        ]
        cycle_specs.append(
            {
                "raw_cycle_id": cycle["raw_cycle_id"],
                "cycle_no": cycle_no,
                "started_at": cycle["start"],
                "ended_at": cycle["end"],
                "sr_seconds": sum(1 for item in records if item["state"] == STATE_SEARCHING),
                "dl_seconds": sum(1 for item in records if item["state"] == STATE_DELIVERING),
                "distance_m": distance_m,
                "avg_speed_kmh": (
                    float(sum(speed_values) / len(speed_values)) if speed_values else 0.0
                ),
                "avg_accuracy_m": (
                    float(sum(accuracy_values) / len(accuracy_values))
                    if accuracy_values
                    else 0.0
                ),
            }
        )

    return cycle_specs


def _build_tracking_session_details(
    *,
    samples: list[ParsedSample],
    vehicle_number: str = "",
):
    gps_df = pd.DataFrame(
        [
            {
                "time": sample.recorded_at,
                "lat": sample.lat,
                "lon": sample.lon,
                "accuracy_m": sample.accuracy_m,
                "speed_kmh": sample.speed_kmh,
            }
            for sample in samples
            if sample.lat is not None and sample.lon is not None
        ]
    )
    if gps_df.empty:
        raise MobileTrackingUploadError("GPS 위치 데이터가 없어 배송 추적을 생성할 수 없습니다.")

    gps_df = _smooth_gps(gps_df)

    ble_df = pd.DataFrame(
        [
            {"time": sample.recorded_at, "rssi": sample.rssi}
            for sample in samples
            if sample.rssi is not None
        ]
    )
    state_series = None
    if not ble_df.empty:
        try:
            state_series = classify_three_states(ble_df[["time", "rssi"]])
        except Exception:
            state_series = None

    capture_events = _extract_capture_events(samples)
    capture_times = [event["captured_at"] for event in capture_events]
    gps_records = []
    distance_m = 0.0
    iv_seconds = 0
    sr_seconds = 0
    dl_seconds = 0
    last_time = None
    prev_lat = None
    prev_lon = None

    for row in gps_df.itertuples(index=False):
        state, raw_cycle_id = _resolve_state(
            row.time,
            row.speed_kmh,
            capture_times,
            state_series,
        )
        record = {
            "recorded_at": row.time,
            "lat": float(row.lat_f),
            "lon": float(row.lon_f),
            "accuracy_m": float(row.accuracy_m or 0.0),
            "speed_kmh": float(row.speed_kmh or 0.0),
            "state": state,
            "raw_cycle_id": raw_cycle_id,
        }
        gps_records.append(record)

        if last_time is not None:
            dt = max(0, int((row.time - last_time).total_seconds()))
            if state == STATE_IN_VEHICLE:
                iv_seconds += dt
            elif state == STATE_SEARCHING:
                sr_seconds += dt
            else:
                dl_seconds += dt
        last_time = row.time

        if prev_lat is not None and prev_lon is not None:
            distance_m += _haversine_m(prev_lat, prev_lon, record["lat"], record["lon"])
        prev_lat = record["lat"]
        prev_lon = record["lon"]

    ble_rows = [
        BleLog(
            recorded_at=sample.recorded_at,
            rssi=sample.rssi,
            status="",
        )
        for sample in samples
        if sample.rssi is not None
    ]

    return {
        "gps_records": gps_records,
        "cycle_specs": _build_cycle_specs(gps_records),
        "ble_rows": ble_rows,
        "capture_events": capture_events,
        "distance_m": distance_m,
        "iv_seconds": iv_seconds,
        "sr_seconds": sr_seconds,
        "dl_seconds": dl_seconds,
        "vehicle_number": vehicle_number,
    }


def populate_tracking_session_details(
    *,
    session: TrackingSession,
    csv_content: str,
    vehicle_number: str = "",
):
    samples = _parse_samples(csv_content)
    details = _build_tracking_session_details(
        samples=samples,
        vehicle_number=vehicle_number,
    )
    gps_records = details["gps_records"]
    cycle_specs = details["cycle_specs"]
    ble_rows = details["ble_rows"]
    capture_events = details["capture_events"]

    with transaction.atomic():
        session = TrackingSession.objects.select_for_update().get(pk=session.pk)
        session.points.all().delete()
        session.ble_logs.all().delete()
        session.captures.all().delete()
        session.cycles.all().delete()

        session.session_date = gps_records[0]["recorded_at"].date()
        session.started_at = gps_records[0]["recorded_at"]
        session.ended_at = gps_records[-1]["recorded_at"]
        session.total_seconds = details["iv_seconds"] + details["sr_seconds"] + details["dl_seconds"]
        session.iv_seconds = details["iv_seconds"]
        session.sr_seconds = details["sr_seconds"]
        session.dl_seconds = details["dl_seconds"]
        session.distance_m = details["distance_m"]
        session.bbox_min_lat = min(record["lat"] for record in gps_records)
        session.bbox_min_lon = min(record["lon"] for record in gps_records)
        session.bbox_max_lat = max(record["lat"] for record in gps_records)
        session.bbox_max_lon = max(record["lon"] for record in gps_records)
        session.cycle_count = len(cycle_specs)
        session.save(
            update_fields=[
                "session_date",
                "started_at",
                "ended_at",
                "total_seconds",
                "iv_seconds",
                "sr_seconds",
                "dl_seconds",
                "distance_m",
                "bbox_min_lat",
                "bbox_min_lon",
                "bbox_max_lat",
                "bbox_max_lon",
                "cycle_count",
                "updated_at",
            ]
        )

        raw_cycle_id_to_db_id = {}
        for spec in cycle_specs:
            cycle = Cycle.objects.create(
                session=session,
                cycle_no=spec["cycle_no"],
                started_at=spec["started_at"],
                ended_at=spec["ended_at"],
                sr_seconds=spec["sr_seconds"],
                dl_seconds=spec["dl_seconds"],
                distance_m=spec["distance_m"],
                avg_speed_kmh=spec["avg_speed_kmh"],
                avg_accuracy_m=spec["avg_accuracy_m"],
            )
            raw_cycle_id_to_db_id[spec["raw_cycle_id"]] = cycle.id

        point_rows = [
            LocationPoint(
                session=session,
                recorded_at=record["recorded_at"],
                lat=record["lat"],
                lon=record["lon"],
                accuracy_m=record["accuracy_m"],
                speed_kmh=record["speed_kmh"],
                state=record["state"],
                cycle_id=raw_cycle_id_to_db_id.get(record["raw_cycle_id"]),
            )
            for record in gps_records
        ]
        LocationPoint.objects.bulk_create(point_rows, batch_size=1000)

        if ble_rows:
            for row in ble_rows:
                row.session = session
            BleLog.objects.bulk_create(ble_rows, batch_size=1000)

        capture_rows = []
        for event in capture_events:
            started_at = event["started_at"]
            captured_at = event["captured_at"]
            anchor_time = captured_at
            duration_ms = 0
            if started_at and captured_at >= started_at:
                duration_ms = int((captured_at - started_at).total_seconds() * 1000)
                anchor_time = started_at + timedelta(seconds=(captured_at - started_at).total_seconds() * 0.8)

            nearest = min(
                gps_records,
                key=lambda item: abs((item["recorded_at"] - anchor_time).total_seconds()),
                default=None,
            )
            capture_rows.append(
                CameraCapture(
                    session=session,
                    started_at=started_at,
                    captured_at=captured_at,
                    duration_ms=max(0, duration_ms),
                    device=vehicle_number[:64],
                    lat=nearest["lat"] if nearest else None,
                    lon=nearest["lon"] if nearest else None,
                    cycle_id=raw_cycle_id_to_db_id.get(nearest["raw_cycle_id"]) if nearest else None,
                )
            )

        if capture_rows:
            CameraCapture.objects.bulk_create(capture_rows, batch_size=200)

        capture_count_by_cycle = {cycle_id: 0 for cycle_id in raw_cycle_id_to_db_id.values()}
        for capture in capture_rows:
            if capture.cycle_id:
                capture_count_by_cycle[capture.cycle_id] = capture_count_by_cycle.get(capture.cycle_id, 0) + 1
        for cycle_id, count in capture_count_by_cycle.items():
            if count:
                Cycle.objects.filter(pk=cycle_id).update(capture_count=count)

    return session


def process_tracking_session_async(
    *,
    session_id: int,
    csv_content: str,
    vehicle_number: str = "",
):
    def runner():
        close_old_connections()
        try:
            session = TrackingSession.objects.select_related("crew_member").get(pk=session_id)
            processed_session = populate_tracking_session_details(
                session=session,
                csv_content=csv_content,
                vehicle_number=vehicle_number,
            )
            try:
                exported_path = export_processed_tracking_csv(
                    processed_session,
                    raw_csv_content=csv_content,
                )
                if exported_path:
                    logger.info(
                        "Exported processed tracking CSV: session_id=%s path=%s",
                        session_id,
                        exported_path,
                    )
            except Exception:
                logger.exception("Failed to export processed tracking CSV: session_id=%s", session_id)
        except Exception:
            logger.exception("Failed to process tracking session asynchronously: session_id=%s", session_id)
        finally:
            close_old_connections()

    thread = threading.Thread(
        target=runner,
        name=f"tracking-session-{session_id}",
        daemon=True,
    )
    thread.start()


def import_mobile_tracking_session(
    *,
    crew: CrewMember,
    csv_content: str,
    vehicle_number: str = "",
    source_name: str = "",
):
    summary = summarize_mobile_tracking_upload(
        csv_content=csv_content,
        source_name=source_name,
    )
    session, _ = get_or_create_tracking_session_stub(
        crew=crew,
        summary=summary,
        vehicle_number=vehicle_number,
    )
    processed_session = populate_tracking_session_details(
        session=session,
        csv_content=csv_content,
        vehicle_number=vehicle_number,
    )
    try:
        export_processed_tracking_csv(
            processed_session,
            raw_csv_content=csv_content,
        )
    except Exception:
        logger.exception("Failed to export processed tracking CSV: session_id=%s", processed_session.pk)
    return processed_session

    samples = _parse_samples(csv_content)
    gps_df = pd.DataFrame(
        [
            {
                "time": sample.recorded_at,
                "lat": sample.lat,
                "lon": sample.lon,
                "accuracy_m": sample.accuracy_m,
                "speed_kmh": sample.speed_kmh,
            }
            for sample in samples
            if sample.lat is not None and sample.lon is not None
        ]
    )
    if gps_df.empty:
        raise MobileTrackingUploadError("GPS 위치 데이터가 없어 배송 추적을 생성할 수 없습니다.")

    gps_df = _smooth_gps(gps_df)

    ble_df = pd.DataFrame(
        [
            {"time": sample.recorded_at, "rssi": sample.rssi}
            for sample in samples
            if sample.rssi is not None
        ]
    )
    state_series = None
    if not ble_df.empty:
        try:
            state_series = classify_three_states(ble_df[["time", "rssi"]])
        except Exception:
            state_series = None

    has_camera_end_events = any(sample.camera_end for sample in samples)
    capture_times = [
        sample.recorded_at
        for sample in samples
        if sample.camera_end or (not has_camera_end_events and sample.camera_captured)
    ]
    gps_records = []
    distance_m = 0.0
    iv_seconds = 0
    sr_seconds = 0
    dl_seconds = 0
    last_time = None
    prev_lat = None
    prev_lon = None

    for row in gps_df.itertuples(index=False):
        state, raw_cycle_id = _resolve_state(
            row.time,
            row.speed_kmh,
            capture_times,
            state_series,
        )
        record = {
            "recorded_at": row.time,
            "lat": float(row.lat_f),
            "lon": float(row.lon_f),
            "accuracy_m": float(row.accuracy_m or 0.0),
            "speed_kmh": float(row.speed_kmh or 0.0),
            "state": state,
            "raw_cycle_id": raw_cycle_id,
        }
        gps_records.append(record)

        if last_time is not None:
            dt = max(0, int((row.time - last_time).total_seconds()))
            if state == STATE_IN_VEHICLE:
                iv_seconds += dt
            elif state == STATE_SEARCHING:
                sr_seconds += dt
            else:
                dl_seconds += dt
        last_time = row.time

        if prev_lat is not None and prev_lon is not None:
            distance_m += _haversine_m(prev_lat, prev_lon, record["lat"], record["lon"])
        prev_lat = record["lat"]
        prev_lon = record["lon"]

    cycle_specs = _build_cycle_specs(gps_records)

    if vehicle_number and crew.vehicle_number != vehicle_number:
        crew.vehicle_number = vehicle_number
        crew.save(update_fields=["vehicle_number", "updated_at"])

    with transaction.atomic():
        session_date = gps_records[0]["recorded_at"].date()
        session = TrackingSession.objects.create(
            crew_member=crew,
            session_date=session_date,
            started_at=gps_records[0]["recorded_at"],
            ended_at=gps_records[-1]["recorded_at"],
            device_id=(source_name or "MOBILE").strip()[:64],
            total_seconds=iv_seconds + sr_seconds + dl_seconds,
            iv_seconds=iv_seconds,
            sr_seconds=sr_seconds,
            dl_seconds=dl_seconds,
            distance_m=distance_m,
            bbox_min_lat=min(record["lat"] for record in gps_records),
            bbox_min_lon=min(record["lon"] for record in gps_records),
            bbox_max_lat=max(record["lat"] for record in gps_records),
            bbox_max_lon=max(record["lon"] for record in gps_records),
        )

        raw_cycle_id_to_db_id = {}
        for spec in cycle_specs:
            cycle = Cycle.objects.create(
                session=session,
                cycle_no=spec["cycle_no"],
                started_at=spec["started_at"],
                ended_at=spec["ended_at"],
                sr_seconds=spec["sr_seconds"],
                dl_seconds=spec["dl_seconds"],
                distance_m=spec["distance_m"],
                avg_speed_kmh=spec["avg_speed_kmh"],
                avg_accuracy_m=spec["avg_accuracy_m"],
            )
            raw_cycle_id_to_db_id[spec["raw_cycle_id"]] = cycle.id

        point_rows = [
            LocationPoint(
                session=session,
                recorded_at=record["recorded_at"],
                lat=record["lat"],
                lon=record["lon"],
                accuracy_m=record["accuracy_m"],
                speed_kmh=record["speed_kmh"],
                state=record["state"],
                cycle_id=raw_cycle_id_to_db_id.get(record["raw_cycle_id"]),
            )
            for record in gps_records
        ]
        LocationPoint.objects.bulk_create(point_rows, batch_size=1000)

        ble_rows = [
            BleLog(
                session=session,
                recorded_at=sample.recorded_at,
                rssi=sample.rssi,
                status="",
            )
            for sample in samples
            if sample.rssi is not None
        ]
        if ble_rows:
            BleLog.objects.bulk_create(ble_rows, batch_size=1000)

        current_camera_started_at = None
        capture_events = []
        for sample in samples:
            if sample.camera_start:
                current_camera_started_at = sample.recorded_at
            if sample.camera_end or (not has_camera_end_events and sample.camera_captured):
                capture_events.append(
                    {
                        "started_at": current_camera_started_at,
                        "captured_at": sample.recorded_at,
                    }
                )
            if sample.camera_end:
                current_camera_started_at = None

        capture_rows = []
        for event in capture_events:
            started_at = event["started_at"]
            captured_at = event["captured_at"]
            anchor_time = captured_at
            duration_ms = 0
            if started_at and captured_at >= started_at:
                duration_ms = int((captured_at - started_at).total_seconds() * 1000)
                anchor_time = started_at + timedelta(seconds=(captured_at - started_at).total_seconds() * 0.8)

            nearest = min(
                gps_records,
                key=lambda item: abs((item["recorded_at"] - anchor_time).total_seconds()),
                default=None,
            )
            capture_rows.append(
                CameraCapture(
                    session=session,
                    started_at=started_at,
                    captured_at=captured_at,
                    duration_ms=max(0, duration_ms),
                    device=vehicle_number[:64],
                    lat=nearest["lat"] if nearest else None,
                    lon=nearest["lon"] if nearest else None,
                    cycle_id=raw_cycle_id_to_db_id.get(nearest["raw_cycle_id"]) if nearest else None,
                )
            )

        if capture_rows:
            CameraCapture.objects.bulk_create(capture_rows, batch_size=200)

        capture_count_by_cycle = {
            cycle_id: 0 for cycle_id in raw_cycle_id_to_db_id.values()
        }
        for capture in capture_rows:
            if capture.cycle_id:
                capture_count_by_cycle[capture.cycle_id] = (
                    capture_count_by_cycle.get(capture.cycle_id, 0) + 1
                )
        for cycle_id, count in capture_count_by_cycle.items():
            if count:
                Cycle.objects.filter(pk=cycle_id).update(capture_count=count)

        session.cycle_count = len(cycle_specs)
        session.save(update_fields=["cycle_count", "updated_at"])

    return session
