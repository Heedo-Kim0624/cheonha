from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.accounts.models import Team
from apps.crew.models import CrewMember
from .models import Settlement, SettlementDetail

User = get_user_model()


class SettlementModelTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(code='A', name='A팀')
        self.settlement = Settlement.objects.create(
            period_start='2024-01-01',
            period_end='2024-01-31',
            team=self.team,
            status='DRAFT'
        )

    def test_settlement_creation(self):
        self.assertEqual(self.settlement.team, self.team)
        self.assertEqual(self.settlement.status, 'DRAFT')
        self.assertEqual(self.settlement.total_profit, 0)

    def test_settlement_str(self):
        self.assertIn(self.team.name, str(self.settlement))

    def test_calculate_profit(self):
        settlement = Settlement.objects.create(
            period_start='2024-02-01',
            period_end='2024-02-29',
            team=self.team,
            total_receive=1000000,
            total_pay=800000,
            total_overtime=50000
        )
        profit = settlement.calculate_profit()
        self.assertEqual(profit, 150000)


class SettlementDetailModelTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(code='A', name='A팀')
        self.crew_member = CrewMember.objects.create(
            code='ZD001',
            name='김배송',
            phone='010-1234-5678',
            team=self.team
        )
        self.settlement = Settlement.objects.create(
            period_start='2024-01-01',
            period_end='2024-01-31',
            team=self.team
        )
        self.detail = SettlementDetail.objects.create(
            settlement=self.settlement,
            crew_member=self.crew_member,
            region='강남구',
            delivery_type='SAME_DAY',
            boxes=100,
            receive_amount=500000,
            pay_amount=400000,
            overtime_cost=20000
        )

    def test_settlement_detail_creation(self):
        self.assertEqual(self.detail.crew_member, self.crew_member)
        self.assertEqual(self.detail.profit, 80000)

    def test_settlement_detail_str(self):
        self.assertIn(str(self.settlement), str(self.detail))
