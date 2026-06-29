from django.db import models

from apps.vehicle_management.models import Company


def normalize_phone(value):
    return ''.join(ch for ch in str(value or '') if ch.isdigit())


class FieldManagerAccount(models.Model):
    """현장관리자 앱 로그인 허용목록."""
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='field_manager_accounts')
    team_code = models.CharField('조', max_length=8, db_index=True)
    phone = models.CharField('전화번호(정규화)', max_length=20, db_index=True)
    display_phone = models.CharField('표시 전화번호', max_length=20, blank=True, default='')
    name = models.CharField('이름', max_length=32, blank=True, default='')
    memo = models.TextField('메모', blank=True, default='')
    is_active = models.BooleanField('사용', default=True, db_index=True)
    last_login_at = models.DateTimeField('마지막 로그인', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'field_mgr"."account'
        ordering = ['company__sort_order', 'team_code', 'phone']
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'team_code', 'phone'],
                name='fm_account_company_team_phone_unique',
            ),
        ]
        indexes = [
            models.Index(fields=['company', 'team_code', 'phone'], name='fm_acct_co_team_phone_idx'),
            models.Index(fields=['is_active', 'company'], name='fm_acct_active_co_idx'),
        ]

    def save(self, *args, **kwargs):
        self.team_code = str(self.team_code or '').strip().upper()
        self.phone = normalize_phone(self.phone)
        if not self.display_phone:
            self.display_phone = self.phone
        super().save(*args, **kwargs)

    def __str__(self):
        label = self.name or self.display_phone or self.phone
        return f'{self.company.code} · {self.team_code}조 · {label}'


class FieldManagerSession(models.Model):
    """현장관리자 로그인 기록 (감사 로그)"""
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False)
    account = models.ForeignKey(
        FieldManagerAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions',
    )
    company_code = models.CharField('회사 코드', max_length=16, db_index=True,
                                     help_text='YUHAN / CHEONHA / PERSONAL')
    team_code = models.CharField('조', max_length=8, db_index=True)
    phone = models.CharField('전화번호', max_length=20, db_index=True)
    user_agent = models.CharField(max_length=255, blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    logged_in_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'field_mgr"."session'
        ordering = ['-logged_in_at']
        indexes = [
            models.Index(fields=['team_code', 'phone'], name='fm_sess_tc_ph_idx'),
        ]

    def __str__(self):
        return f'{self.team_code}조 · {self.phone} · {self.logged_in_at:%Y-%m-%d %H:%M}'
