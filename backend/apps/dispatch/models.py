from django.db import models
from django.contrib.auth import get_user_model
from apps.accounts.models import Team
from apps.common.models import AuditMixin

User = get_user_model()


class DispatchUpload(AuditMixin):
    """배차 데이터 업로드 관리"""
    STATUS_CHOICES = (
        ('PENDING', '검증 대기중'),
        ('VALIDATED', '검증 완료'),
        ('CONFIRMED', '확정'),
        ('ERROR', '오류'),
    )

    file = models.FileField('업로드 파일', upload_to='dispatch/%Y/%m/%d/')
    original_filename = models.CharField('원본 파일명', max_length=500, blank=True, default='')
    dispatch_date = models.DateField('배차일자', null=True, blank=True, help_text='엑셀 파일명에서 추출한 배차 날짜')
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='업로드자'
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='팀'
    )
    upload_date = models.DateTimeField('업로드 일시', auto_now_add=True)
    total_rows = models.IntegerField('총 행 수', default=0)
    success_rows = models.IntegerField('성공 행 수', default=0)
    error_rows = models.IntegerField('오류 행 수', default=0)
    status = models.CharField('상태', max_length=20, choices=STATUS_CHOICES, default='PENDING')
    note = models.TextField('메모', blank=True)

    class Meta:
        verbose_name = '배차 업로드'
        verbose_name_plural = '배차 업로드'
        ordering = ['-upload_date']

    def __str__(self):
        return f'{self.team} - {self.upload_date.strftime("%Y-%m-%d %H:%M")}'


class DispatchRecord(models.Model):
    """배차 레코드"""
    upload = models.ForeignKey(
        DispatchUpload,
        on_delete=models.CASCADE,
        related_name='records',
        verbose_name='업로드'
    )
    row_num = models.IntegerField('행 번호')
    delivery_type = models.CharField('배송타입', max_length=20, blank=True, default='')
    partner_name = models.CharField('파트너사명', max_length=200, blank=True, default='')
    manager_name = models.CharField('담당자명', max_length=100, blank=True, default='')
    sub_region = models.CharField('소지역', max_length=100, blank=True, default='')
    detail_region = models.CharField('상세지역', max_length=100, blank=True, default='')
    households = models.IntegerField('세대수', default=0)
    boxes = models.IntegerField('박스수', default=0)
    original_boxes = models.IntegerField('원본 박스수', default=0, help_text='엑셀 원본 총 박스수 (분리 전)')
    is_split = models.BooleanField('분리여부', default=False, help_text='콤마 분리로 생성된 행')
    split_group = models.IntegerField('분리그룹', default=0, help_text='같은 원본행에서 분리된 레코드 그룹')
    is_overtime = models.BooleanField('특근여부', default=False)
    is_valid = models.BooleanField('유효성', default=False)
    error_message = models.TextField('오류 메시지', blank=True)
    created_at = models.DateTimeField('생성일', auto_now_add=True)

    class Meta:
        verbose_name = '배차 레코드'
        verbose_name_plural = '배차 레코드'
        ordering = ['upload', 'row_num']

    def __str__(self):
        return f'{self.upload.team} - {self.row_num}행'
