"""순수 파이썬 point-in-polygon (ray casting) — GeoJSON Polygon/MultiPolygon 대응."""
from typing import Iterable


def point_in_ring(lon: float, lat: float, ring) -> bool:
    """짝수 교차면 외부. ring: [[lon,lat], ...] 닫혀있어야 함."""
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)):
            xint = (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi
            if lon < xint:
                inside = not inside
        j = i
    return inside


def point_in_polygon(lon: float, lat: float, polygon) -> bool:
    """GeoJSON Polygon coords: [outer, hole1, hole2, ...]"""
    if not polygon:
        return False
    outer = polygon[0]
    if not point_in_ring(lon, lat, outer):
        return False
    for hole in polygon[1:]:
        if point_in_ring(lon, lat, hole):
            return False
    return True


def point_in_geometry(lon: float, lat: float, geom: dict) -> bool:
    if not geom:
        return False
    t = geom.get('type')
    c = geom.get('coordinates')
    if t == 'Polygon':
        return point_in_polygon(lon, lat, c)
    if t == 'MultiPolygon':
        return any(point_in_polygon(lon, lat, p) for p in (c or []))
    return False


def bbox_of_geometry(geom: dict):
    """returns (min_lon, min_lat, max_lon, max_lat) or None."""
    if not geom:
        return None
    coords = []
    t = geom.get('type')
    if t == 'Polygon':
        for ring in geom.get('coordinates') or []:
            coords.extend(ring)
    elif t == 'MultiPolygon':
        for poly in geom.get('coordinates') or []:
            for ring in poly:
                coords.extend(ring)
    if not coords:
        return None
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return (min(xs), min(ys), max(xs), max(ys))
