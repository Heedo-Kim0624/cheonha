from django.db import models
from django.contrib.auth import get_user_model
from apps.accounts.models import Team
from apps.common.models import AuditMixin

User = get_user_model()


class Region(AuditMixin):
    """권역 관리"""
    code = models.CharField('권역코드', max_length=20, unique=True)
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='regions',
        verbose_name='팀'
    )
    name = models.CharField('권역명', max_length=100)
    is_active = models.BooleanField('활성화', default=True)
    note = models.TextField('메모', blank=True)

    class Meta:
        verbose_name = '권역'
        verbose_name_plural = '권역'
        ordering = ['team', 'code']
        unique_together = ('code', 'team')

    def __str__(self):
        return f'{self.code} - {self.name}'


class RegionPrice(AuditMixin):
    """권역별 단가 관리"""
    DELIVERY_TYPE_CHOICES = (
        ('SAME_DAY', '당일'),
        ('NEXT_DAY', '익일'),
    )

    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name='prices',
        verbose_name='권역'
    )
    delivery_type = models.CharField('배송타입', max_length=20, choices=DELIVERY_TYPE_CHOICES)
    receive_price = models.DecimalField(
        '수신단가',
        max_digits=12,
        decimal_places=0,
        help_text='원 단위 - 배송사로부터 수신한 단가 (고정)'
    )
    pay_price = models.DecimalField(
        '지급단가',
        max_digits=12,
        decimal_places=0,
        help_text='원 단위 - 배송원에게 지급하는 단가 (조정 가능)'
    )
    start_date = models.DateField('시작일')
    end_date = models.DateField('종료일', null=True, blank=True)

    class Meta:
        verbose_name = '권역 단가'
        verbose_name_plural = '권역 단가'
        ordering = ['-start_date', 'region']
        unique_together = ('region', 'delivery_type', 'start_date')

    def __str__(self):
        return f'{self.region} - {self.get_delivery_type_display()} ({self.start_date})'


class PriceHistory(AuditMixin):
    """권역 단가 변경 이력"""
    FIELD_CHOICES = (
        ('receive_price', '수신단가'),
        ('pay_price', '지급단가'),
        ('start_date', '시작일'),
        ('end_date', '종료일'),
    )

    region_price = models.ForeignKey(
        RegionPrice,
        on_delete=models.CASCADE,
        related_name='histories',
        verbose_name='권역 단가'
    )
    field_changed = models.CharField('변경 필드', max_length=20, choices=FIELD_CHOICES)
    old_value = models.CharField('이전값', max_length=200)
    new_value = models.CharField('새값', max_length=200)
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='변경자'
    )
    changed_at = models.DateTimeField('변경일시', auto_now_add=True)

    class Meta:
        verbose_name = '권역 단가 이력'
        verbose_name_plural = '권역 단가 이력'
        ordering = ['-changed_at']

    def __str__(self):
        return f'{self.region_price} - {self.field_changed} ({self.changed_at})'
