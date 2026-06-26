"""VWorld Geocoder API 2.0 클라이언트.

https://api.vworld.kr/req/address?service=address&request=getCoord&...
일 40k 건 제한.
"""
import logging
from typing import Optional, Tuple
from urllib.parse import urlencode
from urllib.request import urlopen, Request
import json

from django.conf import settings

logger = logging.getLogger(__name__)

VWORLD_API_KEY = getattr(settings, 'VWORLD_API_KEY', '')
VWORLD_ENDPOINT = 'https://api.vworld.kr/req/address'


def _request_coord(address: str, addr_type: str) -> Optional[dict]:
    """VWorld 에 한 번 요청. 성공 시 payload dict, 실패 시 None."""
    if not VWORLD_API_KEY:
        logger.warning('VWorld geocode skipped: VWORLD_API_KEY is not configured')
        return None

    params = {
        'service': 'address',
        'request': 'getCoord',
        'version': '2.0',
        'crs': 'epsg:4326',
        'address': address,
        'refine': 'true',
        'simple': 'false',
        'format': 'json',
        'type': addr_type,
        'key': VWORLD_API_KEY,
    }
    url = f'{VWORLD_ENDPOINT}?{urlencode(params)}'
    req = Request(url, headers={'User-Agent': 'cheonha-manpower/1.0'})
    try:
        with urlopen(req, timeout=6) as r:
            data = json.loads(r.read().decode('utf-8'))
    except Exception as e:
        logger.warning('VWorld geocode network error: %s', e)
        return None
    resp = (data or {}).get('response') or {}
    if resp.get('status') != 'OK':
        return None
    return resp.get('result')


def geocode_address(address: str) -> Tuple[Optional[float], Optional[float], str]:
    """
    주소 → (lat, lon, error). error 가 빈 문자열이면 성공.
    도로명 실패 시 지번 타입으로 재시도.
    """
    if not address or not address.strip():
        return (None, None, 'empty address')

    addr = address.strip()

    for addr_type in ('road', 'parcel'):
        result = _request_coord(addr, addr_type)
        if not result:
            continue
        point = result.get('point') or {}
        try:
            lon = float(point.get('x'))
            lat = float(point.get('y'))
            return (lat, lon, '')
        except (TypeError, ValueError):
            continue

    return (None, None, 'VWorld lookup failed')
