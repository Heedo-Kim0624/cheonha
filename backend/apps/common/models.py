from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AuditMixin(models.Model):
    """감시 정보를 추가하는 Mixin"""
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
        verbose_name='생성자'
    )
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated',
        verbose_name='수정자'
    )
    updated_at = models.DateTimeField('수정일', auto_now=True)

    class Meta:
        abstract = True
