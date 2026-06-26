import shutil
import tempfile
from datetime import date
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.field_manager.models import FieldManagerAccount
from apps.vehicle_management.models import (
    CalendarEvent,
    Company,
    ReturnRequest,
    ReturnRequestPhoto,
    SubscriptionRequest,
)


class FieldManagerApiTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()

        self.client = APIClient()
        self.cheonha = Company.objects.create(code='CHEONHA', name='천하', sort_order=1)
        self.yuhan = Company.objects.create(code='YUHAN', name='유한', sort_order=2)
        self.account = FieldManagerAccount.objects.create(
            company=self.cheonha,
            team_code='A',
            phone='010-1234-5678',
            display_phone='010-1234-5678',
            name='테스트 관리자',
        )

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def _login(self):
        response = self.client.post(
            '/api/v1/field-manager/login/',
            {
                'company_code': 'CHEONHA',
                'team_code': 'a',
                'phone': '010-1234-5678',
                'pin': '2580',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        return response.data['token']

    def _auth(self):
        return {'HTTP_AUTHORIZATION': f'Bearer {self._login()}'}

    def _image(self, name='photo.jpg', content_type='image/jpeg', size=16):
        return SimpleUploadedFile(name, b'x' * size, content_type=content_type)

    def test_login_rejects_unregistered_field_manager(self):
        response = self.client.post(
            '/api/v1/field-manager/login/',
            {
                'company_code': 'CHEONHA',
                'team_code': 'R',
                'phone': '010-0000-0000',
                'pin': '2580',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn('등록되지 않은 현장관리자', response.data['detail'])

    def test_subscription_request_uses_token_identity_not_request_body(self):
        response = self.client.post(
            '/api/v1/field-manager/subscription-requests/',
            {
                'company_code': 'YUHAN',
                'team_code': 'R',
                'phone': '010-9999-9999',
                'requested_date': '2026-06-10',
                'quantity': 2,
            },
            format='json',
            **self._auth(),
        )

        self.assertEqual(response.status_code, 201, response.content)
        request = SubscriptionRequest.objects.get(id=response.data['id'])
        self.assertEqual(request.company, self.cheonha)
        self.assertEqual(request.team_code, 'A')
        self.assertEqual(request.phone, '01012345678')

    def test_blocked_dates_include_company_and_common_blocks_for_token_company(self):
        CalendarEvent.objects.create(
            company=None,
            kind='BLOCK',
            event_date=date(2026, 7, 15),
            title='전사 공통 불가',
        )
        CalendarEvent.objects.create(
            company=self.cheonha,
            kind='BLOCK',
            event_date=date(2026, 7, 16),
            title='천하 불가',
        )
        CalendarEvent.objects.create(
            company=self.yuhan,
            kind='BLOCK',
            event_date=date(2026, 7, 17),
            title='유한 불가',
        )

        response = self.client.get(
            '/api/v1/field-manager/blocked-dates/',
            {
                'company_code': 'YUHAN',
                'date_from': '2026-07-14',
                'date_to': '2026-07-18',
            },
            **self._auth(),
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn('2026-07-15', response.data['blocked_dates'])
        self.assertIn('2026-07-16', response.data['blocked_dates'])
        self.assertNotIn('2026-07-17', response.data['blocked_dates'])

    def test_return_request_photo_failure_rolls_back_request(self):
        auth = self._auth()
        payload = {
            'company_code': 'YUHAN',
            'team_code': 'R',
            'phone': '010-9999-9999',
            'vehicle_number': '서울12가3456',
            'reason': '차량 교체',
            'hope_date': '2026-06-10',
            'hope_time': '10:00:00',
            'front_photo': self._image('front.jpg'),
            'rear_photo': self._image('rear.jpg'),
            'left_photo': self._image('left.jpg'),
            'right_photo': self._image('right.jpg'),
            'dashboard_photo': self._image('dashboard.jpg'),
        }
        real_create = ReturnRequestPhoto.objects.create
        calls = {'count': 0}

        def flaky_create(*args, **kwargs):
            calls['count'] += 1
            if calls['count'] == 2:
                raise RuntimeError('forced photo failure')
            return real_create(*args, **kwargs)

        self.client.raise_request_exception = False
        with patch('apps.field_manager.views.ReturnRequestPhoto.objects.create', side_effect=flaky_create):
            response = self.client.post(
                '/api/v1/field-manager/return-requests/',
                payload,
                format='multipart',
                **auth,
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(ReturnRequest.objects.count(), 0)
        self.assertEqual(ReturnRequestPhoto.objects.count(), 0)
