from django.db import models
from apps.crew.models import CrewMember
from apps.accounts.models import Team


class SettlementInquiry(models.Model):
    """정산 문의"""
    STATUS_CHOICES = (
        ('OPEN', '미응답'),
        ('ANSWERED', '답변완료'),
        ('READ', '읽음'),
    )

    crew_member = models.ForeignKey(
        CrewMember, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='inquiries', verbose_name='배송원'
    )
    crew_name = models.CharField('배송원 이름', max_length=100)
    team = models.ForeignKey(
        Team, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='inquiries', verbose_name='팀'
    )
    team_name = models.CharField('팀명', max_length=50, blank=True, default='')

    dispatch_date = models.DateField('선택된 날짜')

    # 원본 (기사 조회 시점)
    original_boxes = models.IntegerField('원본 박스수', default=0)
    original_pay_price = models.DecimalField('원본 지급단가', max_digits=12, decimal_places=0, default=0)
    original_adjustment = models.DecimalField('원본 조정금액', max_digits=12, decimal_places=0, default=0)
    original_total = models.DecimalField('원본 정산금액', max_digits=12, decimal_places=0, default=0)

    # 관리자 수정값 (실제 적용)
    boxes = models.IntegerField('박스수', default=0)
    pay_price = models.DecimalField('지급단가', max_digits=12, decimal_places=0, default=0)
    is_overtime = models.BooleanField('특근 여부', default=False)
    adjustment_amount = models.DecimalField(
        '조정금액', max_digits=12, decimal_places=0, default=0,
        help_text='음수 가능'
    )
    total_amount = models.DecimalField('정산금액', max_digits=12, decimal_places=0, default=0)

    # 상태
    status = models.CharField('상태', max_length=20, choices=STATUS_CHOICES, default='OPEN')
    last_by = models.CharField(
        '마지막 발신자', max_length=10, default='crew',
        help_text='crew | admin'
    )

    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    class Meta:
        verbose_name = '정산 문의'
        verbose_name_plural = '정산 문의'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['crew_member', 'dispatch_date'],
                name='unique_inquiry_per_crew_and_date',
            ),
        ]

    def __str__(self):
        return f'{self.crew_name}({self.team_name}) {self.dispatch_date}'


class InquiryMessage(models.Model):
    """정산 문의 댓글"""
    AUTHOR_CHOICES = (
        ('crew', '기사'),
        ('admin', '관리자'),
    )
    inquiry = models.ForeignKey(
        SettlementInquiry, on_delete=models.CASCADE,
        related_name='messages', verbose_name='문의'
    )
    author_type = models.CharField('작성자 구분', max_length=10, choices=AUTHOR_CHOICES)
    author_name = models.CharField('작성자 이름', max_length=100)
    content = models.TextField('내용')
    created_at = models.DateTimeField('작성일', auto_now_add=True)

    class Meta:
        verbose_name = '문의 댓글'
        verbose_name_plural = '문의 댓글'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.inquiry} - {self.author_name}'
