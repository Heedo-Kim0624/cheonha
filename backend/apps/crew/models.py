from django.db import models
from apps.accounts.models import Team
from apps.partner.models import Partner
from apps.common.models import AuditMixin


class CrewMember(AuditMixin):
    """배송원 관리"""
    code = models.CharField('배송원코드', max_length=50, unique=True)
    name = models.CharField('배송원명', max_length=100)
    phone = models.CharField('전화번호', max_length=20)
    vehicle_number = models.CharField('차량번호', max_length=20, blank=True)
    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='팀'
    )
    partner = models.ForeignKey(
        Partner,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='crew_members',
        verbose_name='파트너사'
    )
    region = models.CharField('권역', max_length=50, blank=True)
    is_active = models.BooleanField('활성화', default=True)
    is_new = models.BooleanField('신규', default=False)
    note = models.TextField('메모', blank=True)

    class Meta:
        verbose_name = '배송원'
        verbose_name_plural = '배송원'
        ordering = ['code']
        unique_together = ('code', 'team')

    def __str__(self):
        return f'{self.code} - {self.name}'


class OvertimeSetting(AuditMixin):
    """연장근무 설정"""
    dispatch_upload = models.ForeignKey(
        'dispatch.DispatchUpload',
        on_delete=models.CASCADE,
        related_name='overtime_settings',
        verbose_name='배차 업로드'
    )
    crew_member = models.ForeignKey(
        CrewMember,
        on_delete=models.CASCADE,
        related_name='overtime_settings',
        verbose_name='배송원'
    )
    is_overtime = models.BooleanField('연장근무 여부', default=False)
    overtime_cost = models.DecimalField(
        '연장근무 단가',
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text='원 단위'
    )

    class Meta:
        verbose_name = '연장근무 설정'
        verbose_name_plural = '연장근무 설정'
        ordering = ['dispatch_upload', 'crew_member']
        unique_together = ('dispatch_upload', 'crew_member')

    def __str__(self):
        return f'{self.dispatch_upload} - {self.crew_member}'
