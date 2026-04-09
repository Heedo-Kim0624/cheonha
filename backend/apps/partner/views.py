from rest_framework import viewsets, permissions
from apps.common.views import BaseViewSet
from .models import Partner
from .serializers import PartnerSerializer


class PartnerViewSet(BaseViewSet):
    """파트너사 관리"""
    queryset = Partner.objects.filter(is_active=True)
    serializer_class = PartnerSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['name', 'business_number']
    ordering_fields = ['name', 'contract_start']
