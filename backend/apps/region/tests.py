from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.accounts.models import Team
from .models import Region, RegionPrice

User = get_user_model()


class RegionModelTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(code='A', name='A팀')
        self.region = Region.objects.create(
            code='10A2',
            team=self.team,
            name='강남구'
        )

    def test_region_creation(self):
        self.assertEqual(self.region.code, '10A2')
        self.assertEqual(self.region.team, self.team)
        self.assertTrue(self.region.is_active)

    def test_region_str(self):
        self.assertEqual(str(self.region), '10A2 - 강남구')


class RegionPriceModelTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(code='A', name='A팀')
        self.region = Region.objects.create(
            code='10A2',
            team=self.team,
            name='강남구'
        )
        self.region_price = RegionPrice.objects.create(
            region=self.region,
            delivery_type='SAME_DAY',
            receive_price=5000,
            pay_price=4500,
            start_date='2024-01-01'
        )

    def test_region_price_creation(self):
        self.assertEqual(self.region_price.receive_price, 5000)
        self.assertEqual(self.region_price.pay_price, 4500)

    def test_region_price_str(self):
        self.assertIn('10A2', str(self.region_price))
