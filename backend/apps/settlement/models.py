from django.db import models
from django.contrib.auth import get_user_model
from apps.accounts.models import Team
from apps.crew.models import CrewMember
from apps.common.models import AuditMixin

User = get_user_model()


class Settlement(AuditMixin):
    """정산 관리"""
    STATUS_CHOICES = (
        ('DRAFT', '작성중'),
        ('CONFIRMED', '확정'),
        ('PAID', '지급완료'),
    )

    period_start = models.DateField('정산 시작일')
    period_end = models.DateField('정산 종료일')
    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        related_name='settlements',
        verbose_name='팀'
    )
    status = models.CharField('상태', max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    total_receive = models.DecimalField(
        '총 수신액',
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text='원 단위'
    )
    total_pay = models.DecimalField(
        '총 지급액',
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text='원 단위'
    )
    total_overtime = models.DecimalField(
        '총 연장근무료',
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text='원 단위'
    )
    total_profit = models.DecimalField(
        '총 이윤',
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text='원 단위 (수신액 - 지급액 - 연장근무료)'
    )
    confirmed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_settlements',
        verbose_name='확정자'
    )
    confirmed_at = models.DateTimeField('확정일시', null=True, blank=True)
    note = models.TextField('메모', blank=True)

    class Meta:
        verbose_name = '정산'
        verbose_name_plural = '정산'
        ordering = ['-period_start']
        unique_together = ('team', 'period_start', 'period_end')

    def __str__(self):
        return f'{self.team} - {self.period_start} ~ {self.period_end}'

    def calculate_profit(self):
        """이윤 계산"""
        return self.total_receive - self.total_pay - self.total_overtime


class SettlementDetail(AuditMixin):
    """정산 상세 정보"""
    DELIVERY_TYPE_CHOICES = (
        ('SAME_DAY', '당일'),
        ('NEXT_DAY', '익일'),
    )

    settlement = models.ForeignKey(
        Settlement,
        on_delete=models.CASCADE,
        related_name='details',
        verbose_name='정산'
    )
    crew_member = models.ForeignKey(
        CrewMember,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='배송원'
    )
    region = models.CharField('권역', max_length=100)
    delivery_type = models.CharField('배송타입', max_length=20, choices=DELIVERY_TYPE_CHOICES)
    boxes = models.IntegerField('박스수', default=0)
    receive_amount = models.DecimalField(
        '수신액',
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text='원 단위'
    )
    pay_amount = models.DecimalField(
        '지급액',
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text='원 단위'
    )
    overtime_cost = models.DecimalField(
        '연장근무료',
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text='원 단위'
    )
    profit = models.DecimalField(
        '이윤',
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text='원 단위 (수신액 - 지급액 - 연장근무료)'
    )

    class Meta:
        verbose_name = '정산 상세'
        verbose_name_plural = '정산 상세'
        ordering = ['settlement', 'crew_member']

    def __str__(self):
        return f'{self.settlement} - {self.crew_member}'

    def calculate_profit(self):
        """이윤 계산"""
        return self.receive_amount - self.pay_amount - self.overtime_cost
