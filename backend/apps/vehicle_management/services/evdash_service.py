import os
import hashlib
from datetime import datetime

import psycopg2
import psycopg2.extras
from psycopg2 import sql
from django.core.cache import cache
from django.utils import timezone


EVDASH_LIST_VIEW = 'v_cheonha_vehicle_list'
EVDASH_LATEST_VIEW = 'v_cheonha_vehicle_latest'
EVDASH_FLEET_STATS_VIEW = 'v_cheonha_fleet_stats'
EVDASH_DIAGNOSTIC_TABLE = 'dashboard_diagnostic'


def _cache_ttl() -> int:
    try:
        return max(0, int(os.environ.get('EVDASH_CACHE_TTL', '30')))
    except (TypeError, ValueError):
        return 30


def _db_config() -> dict:
    return {
        'host': os.environ.get('EVDASH_DB_HOST', ''),
        'port': int(os.environ.get('EVDASH_DB_PORT') or 5432),
        'dbname': os.environ.get('EVDASH_DB_NAME', ''),
        'user': os.environ.get('EVDASH_DB_USER', ''),
        'password': os.environ.get('EVDASH_DB_PASSWORD', ''),
    }


def is_configured() -> bool:
    config = _db_config()
    return all(config.get(key) for key in ('host', 'dbname', 'user', 'password'))


def _connect():
    config = _db_config()
    return psycopg2.connect(
        **config,
        connect_timeout=5,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def _digits(value) -> str:
    return ''.join(ch for ch in str(value or '') if ch.isdigit())


def _to_float(value):
    if value in (None, ''):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return str(value)


def _json_row(row):
    if not row:
        return None
    return {key: _iso(value) if hasattr(value, 'isoformat') else value for key, value in dict(row).items()}


def _format_number(value, suffix=''):
    number = _to_float(value)
    if number is None:
        return '-'
    if abs(number - round(number)) < 0.05:
        return f'{int(round(number))}{suffix}'
    return f'{number:.1f}{suffix}'


def _normalize_bool(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {'true', '1', 'yes', 'on'}:
        return True
    if text in {'false', '0', 'no', 'off'}:
        return False
    return None


def _status_label(raw, mapping):
    if raw in (None, ''):
        return '-'
    return mapping.get(str(raw), str(raw))


def _age_seconds(observed_at):
    if not isinstance(observed_at, datetime):
        return None
    observed = observed_at
    if timezone.is_naive(observed):
        observed = timezone.make_aware(observed)
    return max(0, int((timezone.now() - observed).total_seconds()))


def _tone_for_age(age_seconds):
    if age_seconds is None:
        return 'slate'
    if age_seconds <= 15 * 60:
        return 'green'
    if age_seconds <= 60 * 60:
        return 'amber'
    return 'red'


def _location_from_rows(vehicle_row, latest_row):
    lat = _to_float((latest_row or {}).get('latitude'))
    lon = _to_float((latest_row or {}).get('longitude'))
    if lat is None or lon is None:
        x = _to_float((vehicle_row or {}).get('latest_x'))
        y = _to_float((vehicle_row or {}).get('latest_y'))
        if x is not None and y is not None:
            # EV Dashboard x/y may already be WGS84 lon/lat in some payloads.
            if 120 <= x <= 140 and 30 <= y <= 45:
                lon, lat = x, y
            elif 120 <= y <= 140 and 30 <= x <= 45:
                lon, lat = y, x
    if lat is None or lon is None:
        return {'has_location': False, 'latitude': None, 'longitude': None}
    return {'has_location': True, 'latitude': lat, 'longitude': lon}


def _find_vehicle_row(conn, vehicle) -> tuple[dict | None, str]:
    plate = str(getattr(vehicle, 'vehicle_number', '') or '').strip()
    plate_short = str(getattr(vehicle, 'vehicle_number_short', '') or '').strip()
    tid = str(getattr(vehicle, 'vin_tid', '') or '').strip()
    hgi = str(getattr(vehicle, 'hgi', '') or '').strip()
    digits_short = _digits(plate)[-4:] if plate else ''
    params = {
        'plate': plate,
        'plate_short': plate_short or digits_short,
        'digits_short': digits_short,
        'tid': tid,
        'hgi': hgi,
    }
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT *
            FROM {EVDASH_LIST_VIEW}
            WHERE (%(plate)s <> '' AND plate_number = %(plate)s)
               OR (%(plate_short)s <> '' AND plate_short = %(plate_short)s)
               OR (%(digits_short)s <> '' AND plate_short = %(digits_short)s)
               OR (%(tid)s <> '' AND tid = %(tid)s)
               OR (%(hgi)s <> '' AND nickname = %(hgi)s)
            ORDER BY
              CASE
                WHEN plate_number = %(plate)s THEN 0
                WHEN tid = %(tid)s THEN 1
                WHEN plate_short = %(plate_short)s THEN 2
                WHEN plate_short = %(digits_short)s THEN 3
                WHEN nickname = %(hgi)s THEN 4
                ELSE 9
              END,
              last_seen_at DESC NULLS LAST
            LIMIT 1
            """,
            params,
        )
        row = cur.fetchone()
    if not row:
        return None, ''
    if plate and row.get('plate_number') == plate:
        method = 'plate_number'
    elif tid and row.get('tid') == tid:
        method = 'tid'
    elif row.get('plate_short') in {plate_short, digits_short}:
        method = 'plate_short'
    elif hgi and row.get('nickname') == hgi:
        method = 'nickname'
    else:
        method = 'unknown'
    return dict(row), method


def _latest_row(conn, vehicle_id):
    if not vehicle_id:
        return None
    with conn.cursor() as cur:
        cur.execute(
            f'SELECT * FROM {EVDASH_LATEST_VIEW} WHERE vehicle_id = %s LIMIT 1',
            [vehicle_id],
        )
        row = cur.fetchone()
    return dict(row) if row else None


def _latest_rows(conn, vehicle_ids):
    vehicle_ids = [item for item in vehicle_ids if item]
    if not vehicle_ids:
        return {}
    with conn.cursor() as cur:
        cur.execute(
            f'SELECT * FROM {EVDASH_LATEST_VIEW} WHERE vehicle_id = ANY(%s)',
            [vehicle_ids],
        )
        rows = cur.fetchall()
    return {row.get('vehicle_id'): dict(row) for row in rows}


def _fleet_stats(conn, fleet_id):
    if not fleet_id:
        return None
    with conn.cursor() as cur:
        cur.execute(
            f'SELECT * FROM {EVDASH_FLEET_STATS_VIEW} WHERE fleet_id = %s LIMIT 1',
            [fleet_id],
        )
        row = cur.fetchone()
    return dict(row) if row else None


def _build_summary(vehicle_row, latest_row):
    observed_at = (latest_row or {}).get('observed_at') or (vehicle_row or {}).get('last_seen_at')
    age = _age_seconds(observed_at)
    is_online = (vehicle_row or {}).get('is_online')
    if is_online is None and age is not None:
        is_online = age <= 15 * 60
    return {
        'observed_at': _iso(observed_at),
        'age_seconds': age,
        'online': bool(is_online) if is_online is not None else None,
        'online_label': '온라인' if is_online else ('오프라인' if is_online is not None else '미수신'),
        'tone': 'green' if is_online else _tone_for_age(age),
    }


def _build_status_cards(vehicle_row, latest_row):
    latest = latest_row or {}
    key_mapping = {
        'KEY_STATUS_ON': 'ON',
        'KEY_STATUS_OFF': 'OFF',
        'ON': 'ON',
        'OFF': 'OFF',
    }
    charger_mapping = {
        'CHARGER_STATUS_CHARGING': '충전 중',
        'CHARGER_STATUS_CONNECTED': '충전기 연결',
        'CHARGER_STATUS_DISCONNECTED': '미연결',
        'CHARGER_STATUS_NOT_CONNECTED': '미연결',
        'CHARGER_CONNECTION_STATUS_CHARGING': '충전 중',
        'CHARGER_CONNECTION_STATUS_CONNECTED': '충전기 연결',
        'CHARGER_CONNECTION_STATUS_NOT_CHARGING': '충전 안 함',
        'CHARGER_CONNECTION_STATUS_DISCONNECTED': '미연결',
        'CHARGER_CONNECTION_STATUS_NOT_CONNECTED': '미연결',
        'CHARGER_CONNECTED': '충전기 연결',
        'CHARGER_DISCONNECTED': '미연결',
        'CHARGER_CHARGING': '충전 중',
        'CONNECTED': '연결',
        'DISCONNECTED': '미연결',
        'NOT_CONNECTED': '미연결',
        'CHARGING': '충전 중',
    }
    freezer_on = _normalize_bool(latest.get('freezer_on'))
    parking_brake = _normalize_bool(latest.get('parking_brake'))
    return [
        {'key': 'pack_soc', 'label': '배터리', 'value': _format_number(latest.get('pack_soc') or (vehicle_row or {}).get('latest_pack_soc'), '%')},
        {'key': 'range', 'label': '주행가능', 'value': _format_number(latest.get('range_km') or (vehicle_row or {}).get('latest_range'), 'km')},
        {'key': 'speed', 'label': '속도', 'value': _format_number(latest.get('vehicle_speed') or latest.get('veh_speed') or latest.get('gps_speed'), 'km/h')},
        {'key': 'key', 'label': '키 상태', 'value': _status_label(latest.get('key_status') or (vehicle_row or {}).get('latest_key_status'), key_mapping)},
        {'key': 'charger', 'label': '충전', 'value': _status_label(latest.get('charger_status') or (vehicle_row or {}).get('latest_charger_status'), charger_mapping)},
        {'key': 'freezer', 'label': '냉동기', 'value': 'ON' if freezer_on else ('OFF' if freezer_on is not None else '-')},
        {'key': 'temperature', 'label': '현재온도', 'value': _format_number(latest.get('current_temp') or (vehicle_row or {}).get('latest_current_temp'), '°C')},
        {'key': 'parking_brake', 'label': '주차브레이크', 'value': '체결' if parking_brake else ('해제' if parking_brake is not None else '-')},
    ]


def _has_meaningful_error_value(value):
    if value in (None, ''):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip()
    if not text:
        return False
    return text.lower() not in {'0', 'false', 'none', 'null', 'normal', 'ok', 'no_error', 'no error'}


def _detect_errors(*rows):
    tokens = ('error', 'fault', 'dtc', 'diagnostic', 'warning', 'alarm', 'fail')
    found = []
    for row in rows:
        if not row:
            continue
        for key, value in dict(row).items():
            lower = str(key).lower()
            if any(token in lower for token in tokens) and _has_meaningful_error_value(value):
                found.append({'field': key, 'value': str(value)})
    return {
        'has_error': bool(found),
        'items': found[:12],
        'count': len(found),
    }


def _empty_errors():
    return {
        'has_error': False,
        'items': [],
        'count': 0,
        'source': 'dashboard_diagnostic',
    }


def _diagnostic_item(row):
    fault_code = row.get('fault_code')
    severity = row.get('severity') or ''
    description = row.get('description') or ''
    return {
        'field': f'fault_code {fault_code}' if fault_code not in (None, '') else 'fault_code',
        'value': ' · '.join(part for part in [str(severity).strip(), str(description).strip()] if part),
        'fault_code': str(fault_code) if fault_code not in (None, '') else '',
        'severity': str(severity),
        'description': str(description),
        'occurred_at': _iso(row.get('occurrence_time')),
        'is_resolved': bool(row.get('is_resolved')) if row.get('is_resolved') is not None else False,
        'resolved_at': _iso(row.get('maintenance_completion_time')),
        'vehicle_plate_number': row.get('vehicle_plate_number') or '',
        'model_name': row.get('model_name') or '',
    }


def _diagnostic_errors(rows):
    rows = list(rows or [])
    if not rows:
        return _empty_errors()
    return {
        'has_error': True,
        'items': [_diagnostic_item(row) for row in rows[:12]],
        'count': int(rows[0].get('_diagnostic_count') or len(rows)),
        'source': 'dashboard_diagnostic',
    }


def _active_diagnostics_by_terminal(conn, terminal_ids):
    terminal_ids = sorted({int(item) for item in terminal_ids if item})
    if not terminal_ids:
        return {}

    query = sql.SQL(
        """
        WITH ranked AS (
          SELECT
            terminal_id,
            vehicle_plate_number,
            model_name,
            fault_code,
            description,
            severity,
            occurrence_time,
            is_resolved,
            maintenance_completion_time,
            created_at,
            count(*) OVER (PARTITION BY terminal_id) AS _diagnostic_count,
            row_number() OVER (
              PARTITION BY terminal_id
              ORDER BY occurrence_time DESC NULLS LAST, created_at DESC NULLS LAST
            ) AS rn
          FROM {table}
          WHERE terminal_id = ANY(%s)
            AND (is_resolved IS DISTINCT FROM TRUE OR maintenance_completion_time IS NULL)
        )
        SELECT *
        FROM ranked
        WHERE rn <= 12
        ORDER BY terminal_id, occurrence_time DESC NULLS LAST, created_at DESC NULLS LAST
        """
    ).format(table=sql.Identifier(EVDASH_DIAGNOSTIC_TABLE))

    with conn.cursor() as cur:
        cur.execute(query, [terminal_ids])
        rows = [dict(row) for row in cur.fetchall()]

    grouped = {}
    for row in rows:
        grouped.setdefault(row.get('terminal_id'), []).append(row)
    return grouped


def _vehicle_match_params(vehicle):
    plate = str(getattr(vehicle, 'vehicle_number', '') or '').strip()
    plate_short = str(getattr(vehicle, 'vehicle_number_short', '') or '').strip()
    tid = str(getattr(vehicle, 'vin_tid', '') or '').strip()
    hgi = str(getattr(vehicle, 'hgi', '') or '').strip()
    digits_short = _digits(plate)[-4:] if plate else ''
    return {
        'plate': plate,
        'plate_short': plate_short or digits_short,
        'digits_short': digits_short,
        'tid': tid,
        'hgi': hgi,
    }


def _match_score(row, params):
    if params['plate'] and row.get('plate_number') == params['plate']:
        return 0, 'plate_number'
    if params['tid'] and row.get('tid') == params['tid']:
        return 1, 'tid'
    if params['plate_short'] and row.get('plate_short') == params['plate_short']:
        return 2, 'plate_short'
    if params['digits_short'] and row.get('plate_short') == params['digits_short']:
        return 3, 'plate_short'
    if params['hgi'] and row.get('nickname') == params['hgi']:
        return 4, 'nickname'
    return 99, ''


def _sort_ts(value):
    if isinstance(value, datetime):
        return value.timestamp()
    if hasattr(value, 'timestamp'):
        try:
            return value.timestamp()
        except Exception:
            return 0
    return 0


def _fleet_vehicle_rows(conn, vehicles):
    params_by_plate = {
        str(getattr(vehicle, 'vehicle_number', '') or '').strip(): _vehicle_match_params(vehicle)
        for vehicle in vehicles
    }
    plates = sorted({p['plate'] for p in params_by_plate.values() if p['plate']})
    shorts = sorted({
        value
        for p in params_by_plate.values()
        for value in (p['plate_short'], p['digits_short'])
        if value
    })
    tids = sorted({p['tid'] for p in params_by_plate.values() if p['tid']})
    hgis = sorted({p['hgi'] for p in params_by_plate.values() if p['hgi']})
    if not any((plates, shorts, tids, hgis)):
        return {}

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT *
            FROM {EVDASH_LIST_VIEW}
            WHERE plate_number = ANY(%(plates)s)
               OR plate_short = ANY(%(shorts)s)
               OR tid = ANY(%(tids)s)
               OR nickname = ANY(%(hgis)s)
            """,
            {'plates': plates, 'shorts': shorts, 'tids': tids, 'hgis': hgis},
        )
        rows = [dict(row) for row in cur.fetchall()]

    matched = {}
    for plate, match_params in params_by_plate.items():
        candidates = []
        for row in rows:
            score, method = _match_score(row, match_params)
            if score < 99:
                candidates.append((score, _sort_ts(row.get('last_seen_at')), method, row))
        if candidates:
            candidates.sort(key=lambda item: (item[0], item[1]), reverse=False)
            # Same score can have multiple historical fleet rows. Prefer the newest last_seen_at.
            best_score = candidates[0][0]
            best = max([item for item in candidates if item[0] == best_score], key=lambda item: item[1])
            matched[plate] = (best[3], best[2])
    return matched


def get_fleet_evdash(vehicles) -> dict:
    vehicles = list(vehicles or [])
    if not vehicles:
        return {}

    ttl = _cache_ttl()
    cache_seed = '|'.join(
        f'{getattr(vehicle, "id", "")}:{getattr(vehicle, "vehicle_number", "")}:{getattr(vehicle, "updated_at", "")}'
        for vehicle in vehicles
    )
    cache_key = f'evdash_fleet_{hashlib.sha1(cache_seed.encode("utf-8")).hexdigest()}'
    if ttl:
        cached = cache.get(cache_key)
        if cached:
            return cached

    if not is_configured():
        return {
            str(getattr(vehicle, 'vehicle_number', '') or ''): {
                'configured': False,
                'matched': False,
                'detail': 'EVDASH_DB_* 환경변수가 설정되지 않았습니다.',
                'location': {'has_location': False, 'latitude': None, 'longitude': None},
                'summary': {'observed_at': None, 'age_seconds': None, 'online': None, 'online_label': '미수신', 'tone': 'slate'},
                'errors': {'has_error': False, 'items': [], 'count': 0},
            }
            for vehicle in vehicles
        }

    try:
        with _connect() as conn:
            rows_by_plate = _fleet_vehicle_rows(conn, vehicles)
            latest_by_id = _latest_rows(conn, [row.get('vehicle_id') for row, _method in rows_by_plate.values()])
            diagnostics_by_terminal = _active_diagnostics_by_terminal(
                conn,
                [row.get('vehicle_id') for row, _method in rows_by_plate.values()],
            )
            data = {}
            for vehicle in vehicles:
                plate = str(getattr(vehicle, 'vehicle_number', '') or '').strip()
                vehicle_row, match_method = rows_by_plate.get(plate, (None, ''))
                if not vehicle_row:
                    data[plate] = {
                        'configured': True,
                        'matched': False,
                        'detail': 'EV Dashboard 차량 목록에서 일치하는 차량을 찾지 못했습니다.',
                        'location': {'has_location': False, 'latitude': None, 'longitude': None},
                        'summary': {'observed_at': None, 'age_seconds': None, 'online': None, 'online_label': '미수신', 'tone': 'slate'},
                        'errors': _empty_errors(),
                    }
                    continue
                latest_row = latest_by_id.get(vehicle_row.get('vehicle_id'))
                diagnostic_errors = _diagnostic_errors(diagnostics_by_terminal.get(vehicle_row.get('vehicle_id')))
                if not diagnostic_errors.get('has_error'):
                    diagnostic_errors = _detect_errors(vehicle_row, latest_row)
                data[plate] = {
                    'configured': True,
                    'matched': True,
                    'match_method': match_method,
                    'vehicle': _json_row(vehicle_row),
                    'latest': _json_row(latest_row),
                    'location': _location_from_rows(vehicle_row, latest_row),
                    'summary': _build_summary(vehicle_row, latest_row),
                    'errors': diagnostic_errors,
                }
    except Exception as exc:
        data = {
            str(getattr(vehicle, 'vehicle_number', '') or ''): {
                'configured': True,
                'matched': False,
                'detail': f'EV Dashboard 조회 실패: {exc.__class__.__name__}',
                'location': {'has_location': False, 'latitude': None, 'longitude': None},
                'summary': {'observed_at': None, 'age_seconds': None, 'online': None, 'online_label': '미수신', 'tone': 'slate'},
                'errors': _empty_errors(),
            }
            for vehicle in vehicles
        }

    if ttl:
        cache.set(cache_key, data, ttl)
    return data


def get_vehicle_evdash(vehicle) -> dict:
    cache_seed = f'{getattr(vehicle, "id", "")}|{getattr(vehicle, "updated_at", "")}'
    cache_digest = hashlib.sha1(cache_seed.encode('utf-8')).hexdigest()
    cache_key = f'evdash_vehicle_{cache_digest}'
    ttl = _cache_ttl()
    if ttl:
        cached = cache.get(cache_key)
        if cached:
            return cached

    if not is_configured():
        return {
            'configured': False,
            'matched': False,
            'detail': 'EVDASH_DB_* 환경변수가 설정되지 않았습니다.',
            'cache_ttl': ttl,
        }

    try:
        with _connect() as conn:
            vehicle_row, match_method = _find_vehicle_row(conn, vehicle)
            if not vehicle_row:
                data = {
                    'configured': True,
                    'matched': False,
                    'detail': 'EV Dashboard 차량 목록에서 일치하는 차량을 찾지 못했습니다.',
                    'cache_ttl': ttl,
                }
            else:
                latest_row = _latest_row(conn, vehicle_row.get('vehicle_id'))
                fleet_stats = _fleet_stats(conn, vehicle_row.get('fleet_id'))
                diagnostic_errors = _diagnostic_errors(
                    _active_diagnostics_by_terminal(conn, [vehicle_row.get('vehicle_id')]).get(vehicle_row.get('vehicle_id'))
                )
                if not diagnostic_errors.get('has_error'):
                    diagnostic_errors = _detect_errors(vehicle_row, latest_row)
                data = {
                    'configured': True,
                    'matched': True,
                    'match_method': match_method,
                    'cache_ttl': ttl,
                    'vehicle': _json_row(vehicle_row),
                    'latest': _json_row(latest_row),
                    'fleet_stats': _json_row(fleet_stats),
                    'location': _location_from_rows(vehicle_row, latest_row),
                    'summary': _build_summary(vehicle_row, latest_row),
                    'status_cards': _build_status_cards(vehicle_row, latest_row),
                    'errors': diagnostic_errors,
                }
    except Exception as exc:
        data = {
            'configured': True,
            'matched': False,
            'detail': f'EV Dashboard 조회 실패: {exc.__class__.__name__}',
            'cache_ttl': ttl,
        }

    if ttl:
        cache.set(cache_key, data, ttl)
    return data


def check_evdash_connection() -> dict:
    if not is_configured():
        return {'ok': False, 'detail': 'EVDASH_DB_* 환경변수가 설정되지 않았습니다.'}
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT
              (SELECT count(*) FROM {EVDASH_LIST_VIEW}) AS vehicles,
              (SELECT count(*) FROM {EVDASH_LATEST_VIEW}) AS latest,
              (SELECT count(*) FROM {EVDASH_FLEET_STATS_VIEW}) AS fleets,
              (SELECT count(*) FROM {EVDASH_DIAGNOSTIC_TABLE}) AS diagnostics,
              (SELECT count(*) FROM {EVDASH_DIAGNOSTIC_TABLE}
               WHERE is_resolved IS DISTINCT FROM TRUE OR maintenance_completion_time IS NULL) AS active_diagnostics,
              (SELECT max(last_seen_at) FROM {EVDASH_LIST_VIEW}) AS last_seen
            """
        )
        row = dict(cur.fetchone())
    return {
        'ok': True,
        'vehicles': row.get('vehicles'),
        'latest': row.get('latest'),
        'fleets': row.get('fleets'),
        'diagnostics': row.get('diagnostics'),
        'active_diagnostics': row.get('active_diagnostics'),
        'last_seen': _iso(row.get('last_seen')),
    }
