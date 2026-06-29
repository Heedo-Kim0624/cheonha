from django.contrib import admin
from .models import Manpower


@admin.register(Manpower)
class ManpowerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'has_vehicle', 'experience_years', 'address', 'lat', 'lon', 'is_active')
    list_filter = ('has_vehicle', 'is_active')
    search_fields = ('name', 'phone', 'address', 'vehicle_number')
