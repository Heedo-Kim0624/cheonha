from django.test import TestCase
from .models import Partner


class PartnerModelTests(TestCase):
    def setUp(self):
        self.partner = Partner.objects.create(
            name='테스트 배송사',
            business_number='123-45-67890',
            contract_start='2024-01-01'
        )

    def test_partner_creation(self):
        self.assertEqual(self.partner.name, '테스트 배송사')
        self.assertTrue(self.partner.is_active)

    def test_partner_str(self):
        self.assertEqual(str(self.partner), '테스트 배송사')
