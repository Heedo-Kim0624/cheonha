from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Team

User = get_user_model()


class TeamModelTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(
            code='A',
            name='A팀',
            default_overtime_cost=50000
        )

    def test_team_creation(self):
        self.assertEqual(self.team.code, 'A')
        self.assertEqual(self.team.name, 'A팀')
        self.assertTrue(self.team.is_active)

    def test_team_str(self):
        self.assertEqual(str(self.team), 'A팀 (A)')


class UserModelTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(code='A', name='A팀')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='CREW',
            team=self.team
        )

    def test_user_creation(self):
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.role, 'CREW')
        self.assertEqual(self.user.team, self.team)

    def test_user_is_team_leader(self):
        self.assertFalse(self.user.is_team_leader())
        self.user.role = 'TEAM_LEADER'
        self.assertTrue(self.user.is_team_leader())

    def test_user_is_admin(self):
        self.assertFalse(self.user.is_admin())
        self.user.role = 'ADMIN'
        self.assertTrue(self.user.is_admin())


class AuthenticationAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.team = Team.objects.create(code='A', name='A팀')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='CREW',
            team=self.team
        )

    def test_token_obtain(self):
        response = self.client.post('/api/v1/accounts/token/', {
            'username': 'testuser',
            'password': 'testpass123'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_user_me_endpoint(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/accounts/users/me/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['email'], 'test@example.com')

    def test_change_password(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/v1/accounts/users/change_password/', {
            'old_password': 'testpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 새 비밀번호로 로그인 가능한지 확인
        response = self.client.post('/api/v1/accounts/token/', {
            'username': 'testuser',
            'password': 'newpass123'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class UserPermissionTests(APITestCase):
    def setUp(self):
        self.client = APIClient()

        # 팀 생성
        self.team_a = Team.objects.create(code='A', name='A팀')
        self.team_x = Team.objects.create(code='X', name='X팀')

        # 관리자 생성
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            role='ADMIN'
        )

        # 팀장 생성
        self.team_leader_a = User.objects.create_user(
            username='leader_a',
            email='leader_a@example.com',
            password='leaderpass123',
            role='TEAM_LEADER',
            team=self.team_a
        )

        # 팀원 생성
        self.crew_a1 = User.objects.create_user(
            username='crew_a1',
            email='crew_a1@example.com',
            password='crewpass123',
            role='CREW',
            team=self.team_a
        )
        self.crew_a2 = User.objects.create_user(
            username='crew_a2',
            email='crew_a2@example.com',
            password='crewpass123',
            role='CREW',
            team=self.team_a
        )
        self.crew_x = User.objects.create_user(
            username='crew_x',
            email='crew_x@example.com',
            password='crewpass123',
            role='CREW',
            team=self.team_x
        )

    def test_admin_can_see_all_users(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/v1/accounts/users/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 5)

    def test_team_leader_can_see_only_team_members(self):
        self.client.force_authenticate(user=self.team_leader_a)
        response = self.client.get('/api/v1/accounts/users/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 팀장 자신 + 팀원 2명 = 3명
        self.assertEqual(response.data['count'], 3)

    def test_crew_can_see_only_self(self):
        self.client.force_authenticate(user=self.crew_a1)
        response = self.client.get('/api/v1/accounts/users/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['username'], 'crew_a1')
