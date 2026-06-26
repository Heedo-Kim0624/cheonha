from rest_framework import serializers
from .models import Manpower


class ManpowerSerializer(serializers.ModelSerializer):
    has_coords = serializers.BooleanField(read_only=True)

    class Meta:
        model = Manpower
        fields = [
            'id', 'name', 'has_vehicle', 'vehicle_number', 'experience_years',
            'address', 'phone', 'lat', 'lon', 'geocoded_at', 'geocode_error',
            'has_coords', 'note', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'lat', 'lon', 'geocoded_at', 'geocode_error', 'has_coords',
            'created_at', 'updated_at',
        ]
