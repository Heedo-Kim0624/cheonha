import re
from django.db import models
from apps.common.models import AuditMixin


# 권역 코드 "30X4" → 숫자+알파벳+숫자 규칙에서 알파벳 부분을 조(group)로 추출
GROUP_LETTER_RE = re.compile(r'[A-Za-z]+')


def extract_group_letter(code: str) -> str:
    """'30X4' → 'X', 'YD-A2' → 'YDA', 실패 시 ''"""
    if not code:
        return ''
    m = GROUP_LETTER_RE.search(code)
    return m.group(0).upper() if m else ''


class Territory(AuditMixin):
    """권역(배송 폴리곤)."""
    code = models.CharField('권역 코드', max_length=64, unique=True)
    group_letter = models.CharField('조(알파벳)', max_length=8, blank=True, db_index=True)
    team = models.ForeignKey(
        'accounts.Team', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='territories',
    )
    # GeoJSON 'geometry' (Polygon | MultiPolygon). SRID 는 WGS84(EPSG:4326)
    geometry = models.JSONField(default=dict, blank=True)
    centroid_lat = models.FloatField(null=True, blank=True)
    centroid_lon = models.FloatField(null=True, blank=True)
    color = models.CharField('표시 색상', max_length=9, default='#2563EB')
    note = models.TextField('메모', blank=True)

    class Meta:
        verbose_name = '권역'
        verbose_name_plural = '권역'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} ({self.group_letter})'

    def save(self, *args, **kwargs):
        self.group_letter = extract_group_letter(self.code)
        c = _centroid_from_geometry(self.geometry)
        if c:
            self.centroid_lat, self.centroid_lon = c
        else:
            self.centroid_lat = None
            self.centroid_lon = None
        super().save(*args, **kwargs)


class TerritoryBoxRecord(models.Model):
    """권역별 일일 박스 수 (배차표 업로드 시 채움)."""
    territory = models.ForeignKey(
        Territory, related_name='box_records', on_delete=models.CASCADE,
    )
    date = models.DateField(db_index=True)
    box_count = models.FloatField(default=0)
    # 배차표에 권역이 여러 개일 때 분할된 값이면 True
    is_split = models.BooleanField(default=False)

    class Meta:
        unique_together = ('territory', 'date')
        ordering = ['-date']


def _centroid_from_geometry(geom):
    """GeoJSON geometry → (lat, lon) centroid (단순 평균)."""
    if not geom:
        return None
    coords = _collect_coords(geom)
    if not coords:
        return None
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return (sum(ys) / len(ys), sum(xs) / len(xs))


def _collect_coords(geom):
    """GeoJSON 에서 평평한 좌표 리스트 추출."""
    if not isinstance(geom, dict):
        return []
    t = geom.get('type')
    c = geom.get('coordinates')
    if t == 'Polygon' and c:
        return [pt for ring in c for pt in ring]
    if t == 'MultiPolygon' and c:
        out = []
        for poly in c:
            for ring in poly:
                out.extend(ring)
        return out
    return []
