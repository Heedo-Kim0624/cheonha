from django.apps import AppConfig


class FieldManagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.field_manager'
    label = 'field_manager'
    verbose_name = '현장관리자 앱 (Field Manager)'
