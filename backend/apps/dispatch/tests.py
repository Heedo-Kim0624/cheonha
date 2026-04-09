from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from apps.accounts.models import Team
from .models import DispatchUpload, DispatchRecord

User = get_user_model()


class DispatchUploadTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(code='A', name='A팀')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='TEAM_LEADER',
            team=self.team
        )
        self.dispatch_upload = DispatchUpload.objects.create(
            uploaded_by=self.user,
            team=self.team,
            status='PENDING'
        )

    def test_dispatch_upload_creation(self):
        self.assertEqual(self.dispatch_upload.team, self.team)
        self.assertEqual(self.dispatch_upload.status, 'PENDING')

    def test_dispatch_upload_str(self):
        self.assertIn(self.team.name, str(self.dispatch_upload))


class DispatchAPITests(APITestCase):
    def setUp(self):
        self.team_a = Team.objects.create(code='A', name='A팀')
        self.team_leader = User.objects.create_user(
            username='leader',
            email='leader@example.com',
            password='testpass123',
            role='TEAM_LEADER',
            team=self.team_a
        )
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            role='ADMIN'
        )

    def test_team_leader_can_view_own_uploads(self):
        self.client.force_authenticate(user=self.team_leader)

        dispatch_upload = DispatchUpload.objects.create(
            uploaded_by=self.team_leader,
            team=self.team_a,
            status='PENDING'
        )

        response = self.client.get('/api/v1/dispatch/uploads/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_admin_can_view_all_uploads(self):
        self.client.force_authenticate(user=self.admin)

        team_x = Team.objects.create(code='X', name='X팀')
        user_x = User.objects.create_user(
            username='user_x',
            email='user_x@example.com',
            password='testpass123',
            role='CREW',
            team=team_x
        )

        DispatchUpload.objects.create(
            uploaded_by=self.team_leader,
            team=self.team_a,
            status='PENDING'
        )
        DispatchUpload.objects.create(
            uploaded_by=user_x,
            team=team_x,
            status='PENDING'
        )

        response = self.client.get('/api/v1/dispatch/uploads/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
