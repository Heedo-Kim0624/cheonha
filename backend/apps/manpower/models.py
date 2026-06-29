from django.db import models
from apps.common.models import AuditMixin


class Manpower(AuditMixin):
    """인력 풀 (공유시트와 연동되는 기사 후보 레코드)."""
    name = models.CharField('이름', max_length=100)
    has_vehicle = models.BooleanField('차량 유무', default=False)
    vehicle_number = models.CharField('차량 번호', max_length=20, blank=True)
    experience_years = models.PositiveIntegerField('경력(년)', default=0)
    address = models.CharField('거주지', max_length=255, blank=True)
    phone = models.CharField('휴대폰', max_length=20, blank=True)

    # VWorld geocoding 결과 캐싱 (재요청 방지)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    geocoded_at = models.DateTimeField(null=True, blank=True)
    geocode_error = models.CharField(max_length=255, blank=True)

    note = models.TextField('메모', blank=True)
    is_active = models.BooleanField('활성화', default=True)

    class Meta:
        verbose_name = '인력'
        verbose_name_plural = '인력 풀'
        ordering = ['-created_at', 'name']

    def __str__(self):
        return f'{self.name} ({self.phone or "번호없음"})'

    @property
    def has_coords(self):
        return self.lat is not None and self.lon is not None
