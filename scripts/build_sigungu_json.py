"""
BND_SIGUNGU_PG (EPSG:5186, 한국 GRS80 중부원점) shapefile → WGS84 JSON 추출.

출력: backend/apps/manpower/sigungu_centroids.json
{
  "by_sido_sigungu": { "서울특별시 종로구": {"code":"11010","lat":..,"lon":..}, ... },
  "by_sigungu": { "종로구": {...}, ... },
  "sido_map": { "11": "서울특별시", "26": "부산광역시", ... }
}

행정안전부 시도 코드: 시군구 코드의 앞 2자리.
"""
import json
import math
import os
import sys

import shapefile
from pyproj import Transformer


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..'))
SHP = os.path.join(REPO, '_tmp_sigungu', 'BND_SIGUNGU_PG')
OUT = os.path.join(REPO, 'backend', 'apps', 'manpower', 'sigungu_centroids.json')

# 행정안전부 시도 코드 앞 2자리
SIDO = {
    '11': '서울특별시', '26': '부산광역시', '27': '대구광역시', '28': '인천광역시',
    '29': '광주광역시', '30': '대전광역시', '31': '울산광역시', '36': '세종특별자치시',
    '41': '경기도', '42': '강원특별자치도', '43': '충청북도', '44': '충청남도',
    '45': '전북특별자치도', '46': '전라남도', '47': '경상북도', '48': '경상남도', '50': '제주특별자치도',
}


def _polygon_area_centroid(ring):
    """2D polygon centroid (list of [x,y], closed or open). 자체교차 없는 단순 폴리곤 가정."""
    n = len(ring)
    if n < 3:
        return None, 0.0
    a = 0.0
    cx = cy = 0.0
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        cross = x1 * y2 - x2 * y1
        a += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    a *= 0.5
    if abs(a) < 1e-9:
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        return (sum(xs) / n, sum(ys) / n), abs(a)
    return (cx / (6 * a), cy / (6 * a)), abs(a)


def main():
    tr = Transformer.from_crs('EPSG:5186', 'EPSG:4326', always_xy=True)
    sf = shapefile.Reader(SHP, encoding='cp949')
    fields = [f[0] for f in sf.fields[1:]]
    idx_cd = fields.index('SIGUNGU_CD')
    idx_nm = fields.index('SIGUNGU_NM')

    by_sido_sigungu = {}
    by_sigungu = {}  # 단일 이름 (중의성 있으면 서울/가장 큰 면적으로 결정)
    sigungu_seen = {}  # 이름 → (area, entry)

    for shp, rec in zip(sf.shapes(), sf.records()):
        code = rec[idx_cd]
        name = rec[idx_nm]
        if not name:
            continue
        sido_cd = code[:2]
        sido = SIDO.get(sido_cd, '')

        # Multi-part polygon: 부분별로 centroid/area 계산 후 면적 가중평균
        parts = list(shp.parts) + [len(shp.points)]
        total_area = 0.0
        cx_sum = cy_sum = 0.0
        for i in range(len(parts) - 1):
            ring = shp.points[parts[i]:parts[i + 1]]
            if len(ring) < 3:
                continue
            (cx, cy), area = _polygon_area_centroid(ring)
            total_area += area
            cx_sum += cx * area
            cy_sum += cy * area
        if total_area <= 0:
            continue
        cx = cx_sum / total_area
        cy = cy_sum / total_area

        lon, lat = tr.transform(cx, cy)
        entry = {
            'code': code,
            'lat': round(lat, 6),
            'lon': round(lon, 6),
            'sido': sido,
        }

        key = f'{sido} {name}'.strip()
        by_sido_sigungu[key] = entry

        # 동일 이름이 여러 시도에 있을 수 있음 — 서울시를 우선, 그 외는 면적 큰 쪽 유지
        if name not in sigungu_seen:
            sigungu_seen[name] = (total_area, entry, sido)
            by_sigungu[name] = entry
        else:
            prev_area, prev_entry, prev_sido = sigungu_seen[name]
            # 서울 우선
            if sido == '서울특별시' and prev_sido != '서울특별시':
                sigungu_seen[name] = (total_area, entry, sido)
                by_sigungu[name] = entry
            elif prev_sido != '서울특별시' and total_area > prev_area:
                sigungu_seen[name] = (total_area, entry, sido)
                by_sigungu[name] = entry

    out = {
        'sido_map': SIDO,
        'by_sigungu': by_sigungu,
        'by_sido_sigungu': by_sido_sigungu,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f'[OK] wrote {OUT}')
    print(f'   by_sigungu: {len(by_sigungu)} entries')
    print(f'   by_sido_sigungu: {len(by_sido_sigungu)} entries')
    # sanity: 서울 강남구
    s = by_sido_sigungu.get('서울특별시 강남구')
    if s:
        print(f'   sample — 서울 강남구: {s}')


if __name__ == '__main__':
    main()
