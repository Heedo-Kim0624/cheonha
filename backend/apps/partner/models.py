from django.db import models
from apps.common.models import AuditMixin


class Partner(AuditMixin):
    """파트너사 관리"""
    name = models.CharField('파트너사명', max_length=200, unique=True)
    business_number = models.CharField('사업자번호', max_length=20, blank=True, default='')
    contract_start = models.DateField('계약 시작일', null=True, blank=True)
    contract_end = models.DateField('계약 종료일', null=True, blank=True)
    is_active = models.BooleanField('활성화', default=True)
    note = models.TextField('메모', blank=True)

    class Meta:
        verbose_name = '파트너사'
        verbose_name_plural = '파트너사'
        ordering = ['name']

    def __str__(self):
        return self.name
