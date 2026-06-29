from datetime import time as dtime
from pathlib import Path

from django.db.models import Q
from rest_framework import serializers

from apps.vehicle_management.holiday_utils import holiday_dates_between
from apps.vehicle_management.models import (
    CalendarEvent,
    Company,
)
from .models import normalize_phone


RETURN_PHOTO_FIELD_NAMES = {
    'front_photo': 'FRONT',
    'rear_photo': 'REAR',
    'left_photo': 'LEFT',
    'right_photo': 'RIGHT',
    'dashboard_photo': 'DASHBOARD',
}
MAX_RETURN_PHOTO_BYTES = 10 * 1024 * 1024
ALLOWED_RETURN_PHOTO_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif'}


def validate_blocked_calendar_date(company: Company, target_date, field_name: str):
    if CalendarEvent.objects.filter(
        Q(company=company) | Q(company__isnull=True),
        event_date=target_date,
        kind='BLOCK',
    ).exists():
        raise serializers.ValidationError({
            field_name: '관리자가 등록한 불가 날짜입니다.',
        })
    if target_date.isoformat() in holiday_dates_between(target_date, target_date):
        raise serializers.ValidationError({
            field_name: '공휴일은 선택할 수 없습니다.',
        })


class FieldManagerLoginSerializer(serializers.Serializer):
    company_code = serializers.CharField(max_length=16)
    team_code = serializers.CharField(max_length=8)
    phone = serializers.CharField(max_length=20)
    pin = serializers.CharField(max_length=8)

    def validate_company_code(self, value):
        return str(value or '').strip().upper()

    def validate_team_code(self, value):
        value = str(value or '').strip().upper()
        if not value:
            raise serializers.ValidationError('조를 입력해 주세요.')
        return value

    def validate_phone(self, value):
        normalized = normalize_phone(value)
        if not normalized:
            raise serializers.ValidationError('전화번호를 입력해 주세요.')
        return normalized

    def validate_pin(self, value):
        if value != '2580':
            raise serializers.ValidationError('비밀번호가 일치하지 않습니다.')
        return value


class FmSubscriptionRequestSerializer(serializers.Serializer):
    company_code = serializers.CharField(max_length=16, required=False, allow_blank=True)
    team_code = serializers.CharField(max_length=8, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    requested_date = serializers.DateField()
    quantity = serializers.IntegerField(min_value=1)


class FmReturnRequestSerializer(serializers.Serializer):
    company_code = serializers.CharField(max_length=16, required=False, allow_blank=True)
    team_code = serializers.CharField(max_length=8, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    vehicle_number = serializers.CharField(max_length=32)
    reason = serializers.CharField()
    hope_date = serializers.DateField()
    hope_time = serializers.TimeField()
    front_photo = serializers.FileField()
    rear_photo = serializers.FileField()
    left_photo = serializers.FileField()
    right_photo = serializers.FileField()
    dashboard_photo = serializers.FileField()

    def validate_hope_time(self, value: dtime):
        if value.hour < 10 or value.hour >= 17 or (value.hour == 16 and value.minute > 0):
            raise serializers.ValidationError('희망 시간은 10:00~16:00 사이여야 합니다.')
        return value

    def validate(self, attrs):
        for field_name in RETURN_PHOTO_FIELD_NAMES:
            uploaded = attrs.get(field_name)
            content_type = str(getattr(uploaded, 'content_type', '') or '').lower()
            extension = Path(str(getattr(uploaded, 'name', '') or '')).suffix.lower()
            size = int(getattr(uploaded, 'size', 0) or 0)
            if uploaded is None or not content_type.startswith('image/'):
                raise serializers.ValidationError({
                    field_name: '이미지 파일만 업로드할 수 있습니다.',
                })
            if extension not in ALLOWED_RETURN_PHOTO_EXTENSIONS:
                raise serializers.ValidationError({
                    field_name: 'JPG, PNG, WEBP, HEIC 이미지 파일만 업로드할 수 있습니다.',
                })
            if size > MAX_RETURN_PHOTO_BYTES:
                raise serializers.ValidationError({
                    field_name: '사진은 장당 10MB 이하만 업로드할 수 있습니다.',
                })
        return attrs


class FmASRequestSerializer(serializers.Serializer):
    company_code = serializers.CharField(max_length=16, required=False, allow_blank=True)
    team_code = serializers.CharField(max_length=8, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    vehicle_number = serializers.CharField(max_length=32)
    owner_name = serializers.CharField(max_length=32)
    owner_phone = serializers.CharField(max_length=20)
    reason = serializers.CharField()


class FmBlockedDatesQuerySerializer(serializers.Serializer):
    company_code = serializers.CharField(max_length=16, required=False, allow_blank=True)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
