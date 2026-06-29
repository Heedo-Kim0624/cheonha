"""
시군구 이름 → 대표 좌표(lat, lon) 룩업.

데이터 출처: 행정안전부 BND_SIGUNGU_PG shapefile (KGD2002 중부원점 / EPSG:5186) 를
`scripts/build_sigungu_json.py` 로 파싱해 WGS84 중심점 + 면적가중 centroid 로 변환한 JSON.

lookup() 은 다음 순서로 매칭:
  1) '시도 + 시군구' 복합키 (도시명 포함된 입력에 대해 명확히 매칭)
  2) 축약 복합키 ('서울 중구' → '서울특별시 중구')
  3) 단일 시군구명 (중의성 있으면 서울 우선, 그 외는 면적 큰 쪽)
  4) 끝 토큰부터 n 개 조합으로 재시도 ('고양시 일산동구' → '일산동구')
"""
import json
import os
from typing import Optional, Tuple

Coord = Tuple[float, float]

_HERE = os.path.dirname(os.path.abspath(__file__))
_JSON_PATH = os.path.join(_HERE, 'sigungu_centroids.json')

try:
    with open(_JSON_PATH, encoding='utf-8') as _f:
        _DATA = json.load(_f)
except FileNotFoundError:
    _DATA = {'by_sigungu': {}, 'by_sido_sigungu': {}, 'sido_map': {}}

BY_SIGUNGU = _DATA.get('by_sigungu') or {}
BY_SIDO_SIGUNGU = _DATA.get('by_sido_sigungu') or {}

# 시도 축약 → 풀네임 (사용자 입력이 '서울' 처럼 약어로 올 때를 처리)
SIDO_ALIAS = {
    '서울': '서울특별시', '부산': '부산광역시', '대구': '대구광역시',
    '인천': '인천광역시', '광주': '광주광역시', '대전': '대전광역시',
    '울산': '울산광역시', '세종': '세종특별자치시',
    '경기': '경기도', '강원': '강원특별자치도',
    '충북': '충청북도', '충남': '충청남도',
    '전북': '전북특별자치도', '전남': '전라남도',
    '경북': '경상북도', '경남': '경상남도',
    '제주': '제주특별자치도',
}


def _normalize(s: str) -> str:
    if not s:
        return ''
    s = s.strip()
    for pfx in ('대한민국 ', '한국 '):
        if s.startswith(pfx):
            s = s[len(pfx):]
    return ' '.join(s.split())


def _expand_sido(token: str) -> str:
    return SIDO_ALIAS.get(token, token)


def lookup(address: str) -> Optional[Coord]:
    """거주지 문자열 → (lat, lon). 실패 시 None."""
    if not address:
        return None
    s = _normalize(address)
    tokens = s.split()
    if not tokens:
        return None

    # 1) 전체 문자열을 그대로 by_sido_sigungu 에 매칭
    if s in BY_SIDO_SIGUNGU:
        e = BY_SIDO_SIGUNGU[s]
        return (e['lat'], e['lon'])

    # 2) 첫 토큰을 시도 풀네임으로 확장하여 재시도
    expanded = _expand_sido(tokens[0])
    if expanded != tokens[0]:
        key = ' '.join([expanded] + tokens[1:])
        if key in BY_SIDO_SIGUNGU:
            e = BY_SIDO_SIGUNGU[key]
            return (e['lat'], e['lon'])
        # 마지막 토큰만 사용 ('서울 성북구' 형태)
        if tokens[-1] and (' '.join([expanded, tokens[-1]]) in BY_SIDO_SIGUNGU):
            e = BY_SIDO_SIGUNGU[' '.join([expanded, tokens[-1]])]
            return (e['lat'], e['lon'])

    # 3) 끝에서 n 개 토큰 조합으로 by_sido_sigungu 검색
    for n in range(len(tokens), 1, -1):
        key = ' '.join(tokens[-n:])
        if key in BY_SIDO_SIGUNGU:
            e = BY_SIDO_SIGUNGU[key]
            return (e['lat'], e['lon'])

    # 4) 단일 시군구명 매칭 (중의성 있으면 서울 우선)
    for n in range(min(3, len(tokens)), 0, -1):
        key = ' '.join(tokens[-n:])
        if key in BY_SIGUNGU:
            e = BY_SIGUNGU[key]
            return (e['lat'], e['lon'])

    return None
