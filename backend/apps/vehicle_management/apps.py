from django.apps import AppConfig


class VehicleManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.vehicle_management'
    label = 'vehicle_management'
    verbose_name = '차량 관리 (Vehicle Management)'
