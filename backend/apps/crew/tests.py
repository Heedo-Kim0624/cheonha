from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.accounts.models import Team
from apps.partner.models import Partner
from .models import CrewMember, OvertimeSetting

User = get_user_model()


class CrewMemberModelTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(code='A', name='A팀')
        self.partner = Partner.objects.create(
            name='테스트 배송사',
            business_number='123-45-67890',
            contract_start='2024-01-01'
        )
        self.crew_member = CrewMember.objects.create(
            code='ZD001',
            name='김배송',
            phone='010-1234-5678',
            team=self.team,
            partner=self.partner
        )

    def test_crew_member_creation(self):
        self.assertEqual(self.crew_member.code, 'ZD001')
        self.assertEqual(self.crew_member.name, '김배송')
        self.assertEqual(self.crew_member.team, self.team)

    def test_crew_member_str(self):
        self.assertEqual(str(self.crew_member), 'ZD001 - 김배송')

    def test_crew_member_is_new(self):
        self.crew_member.is_new = True
        self.crew_member.save()
        self.assertTrue(self.crew_member.is_new)
