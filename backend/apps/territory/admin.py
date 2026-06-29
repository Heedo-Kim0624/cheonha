from django.contrib import admin
from .models import Territory, TerritoryBoxRecord


@admin.register(Territory)
class TerritoryAdmin(admin.ModelAdmin):
    list_display = ('code', 'group_letter', 'team', 'centroid_lat', 'centroid_lon')
    list_filter = ('group_letter', 'team')
    search_fields = ('code', 'note')


@admin.register(TerritoryBoxRecord)
class TerritoryBoxAdmin(admin.ModelAdmin):
    list_display = ('territory', 'date', 'box_count', 'is_split')
    list_filter = ('date',)
