from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _


class Team(models.Model):
    """팀 정보 관리 - 배차 업로드 시 권역코드에서 자동 생성"""
    code = models.CharField('팀 코드', max_length=10, unique=True)
    name = models.CharField('팀명', max_length=100)
    leader = models.OneToOneField(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_team',
        verbose_name='팀장'
    )
    receive_price = models.DecimalField(
        '수신단가(박스당)',
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text='원 단위 - 택배사로부터 받는 박스당 단가'
    )
    pay_price = models.DecimalField(
        '지급단가(박스당)',
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text='원 단위 - 배송원에게 지급하는 박스당 단가'
    )
    default_overtime_cost = models.DecimalField(
        '기본 특근비용',
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text='원 단위 - 1인당 특근 비용'
    )
    is_active = models.BooleanField('활성화', default=True)
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    class Meta:
        verbose_name = '팀'
        verbose_name_plural = '팀'
        ordering = ['code']

    def __str__(self):
        return f'{self.name} ({self.code})'


class CustomUserManager(BaseUserManager):
    """사용자 관리자"""

    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError('사용자명은 필수입니다.')
        if not email:
            raise ValueError('이메일은 필수입니다.')

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('슈퍼유저는 is_staff=True여야 합니다.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('슈퍼유저는 is_superuser=True여야 합니다.')

        return self.create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    """사용자 모델"""
    ROLE_CHOICES = (
        ('ADMIN', '관리자'),
        ('APPROVER', '승인자'),
        ('TEAM_LEADER', '팀장'),
        ('CREW', '배송원'),
    )

    role = models.CharField('역할', max_length=20, choices=ROLE_CHOICES, default='CREW')
    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
        verbose_name='팀'
    )
    phone = models.CharField('전화번호', max_length=20, blank=True)
    is_active = models.BooleanField('활성화', default=True)
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    objects = CustomUserManager()

    class Meta:
        verbose_name = '사용자'
        verbose_name_plural = '사용자'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_role_display()})'

    def has_team(self):
        """팀이 있는지 확인"""
        return self.team is not None

    def is_team_leader(self):
        """팀장 여부 확인"""
        return self.role == 'TEAM_LEADER'

    def is_admin(self):
        """관리자 여부 확인"""
        return self.role == 'ADMIN'

    def is_approver(self):
        """승인자 여부 확인"""
        return self.role == 'APPROVER'
