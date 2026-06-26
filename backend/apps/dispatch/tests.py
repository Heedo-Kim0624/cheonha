from datetime import date

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from apps.accounts.models import Team
from apps.crew.models import CrewMember, YongchaPayGroup
from apps.settlement.models import Settlement, SettlementDetail
from .date_utils import date_iso, to_delivery_date, to_work_date
from .models import DispatchUpload, DispatchRecord
from .operation_report_services import (
    build_operation_report_amount_lookup,
    build_operation_report_csv_header,
    build_operation_report_csv_row,
    build_operation_report_summary,
)
from .settlement_services import (
    build_crew_settlement_payload,
)
from .text_parsers import parse_coupang_dispatch_text

User = get_user_model()


class DispatchDateUtilsTests(TestCase):
    def test_delivery_date_helpers_shift_one_day(self):
        work_date = date(2026, 5, 13)
        delivery_date = date(2026, 5, 14)

        self.assertEqual(to_delivery_date(work_date), delivery_date)
        self.assertEqual(to_work_date(delivery_date), work_date)
        self.assertEqual(date_iso(delivery_date), '2026-05-14')


class CoupangTextParserTests(TestCase):
    def test_parse_coupang_dispatch_text(self):
        raw_text = "\n".join([
            "F3 예상 물량 공유드립니다.",
            "이브이앤솔루션 주식회사/EVASS | 이름 | 건수 | 가구수",
            "107A | 황*주 (nam | 27 | 21",
            "107B | 황*주 (nam | 36 | 28",
            "107C | 이*혁 (cmd | 29 | 23",
            "107D | 이*혁 (cmd | 32 | 24",
            "108C | 천*열 (mag | 18 | 11",
            "108D | 김*규 (tim | 54 | 29",
            "113C | 최*성 (cms | 20 | 14",
            "113D | 최*성 (cms | 30 | 22",
        ])

        parsed = parse_coupang_dispatch_text(raw_text)

        self.assertEqual(len(parsed.rows), 8)
        self.assertEqual(parsed.total_boxes, 246)
        self.assertEqual(parsed.total_households, 172)
        self.assertEqual(parsed.errors, [])
        self.assertEqual(parsed.rows[0]["sub_region"], "107A")
        self.assertEqual(parsed.rows[0]["manager_name"], "황*주 (nam")
        self.assertEqual(parsed.rows[0]["boxes"], 27)
        self.assertEqual(parsed.rows[0]["households"], 21)


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


class YongchaPayGroupSettlementTests(TestCase):
    def setUp(self):
        self.delivery_date = date(2026, 5, 20)
        self.team = Team.objects.create(
            code='A',
            name='A팀',
            receive_price=0,
            yongcha_pay_price=2500,
        )
        self.pay_group = YongchaPayGroup.objects.create(
            company_app='cheonha',
            name='TS용차',
            round_1_base_pay=160000,
            round_1_base_households=50,
            round_1_extra_household_pay=3000,
            round_2_base_pay=160000,
            round_2_base_households=50,
            round_2_extra_household_pay=3000,
            exclude_base_pay_on_multi_round=True,
        )
        self.crew = CrewMember.objects.create(
            code='driver-a',
            name='driver-a',
            team=self.team,
            is_yongcha=True,
            yongcha_pay_price=2500,
            yongcha_pay_group=self.pay_group,
        )
        self.upload_1 = DispatchUpload.objects.create(
            team=self.team,
            dispatch_date=self.delivery_date,
            round_no=1,
            status='PENDING',
        )
        self.record_1 = DispatchRecord.objects.create(
            upload=self.upload_1,
            row_num=1,
            manager_name=self.crew.code,
            sub_region='A1',
            detail_region='A1',
            boxes=27,
            households=21,
            is_valid=True,
        )

    def _payload(self, upload, record):
        return build_crew_settlement_payload(
            crew_member=self.crew,
            dispatch_upload=upload,
            records=[record],
            receive_price=0,
        )

    def test_yongcha_group_base_pay_applies_when_driver_has_one_yongcha_round_that_day(self):
        payload = self._payload(self.upload_1, self.record_1)

        self.assertEqual(payload['pay_basis'], 'yongcha_pay_group')
        self.assertEqual(int(payload['total_pay']), 160000)
        self.assertEqual(payload['daily_yongcha_round_count'], 1)

    def test_yongcha_group_base_pay_is_skipped_when_driver_has_multiple_yongcha_rounds_that_day(self):
        upload_2 = DispatchUpload.objects.create(
            team=self.team,
            dispatch_date=self.delivery_date,
            round_no=2,
            status='PENDING',
        )
        record_2 = DispatchRecord.objects.create(
            upload=upload_2,
            row_num=1,
            manager_name=self.crew.code,
            sub_region='A2',
            detail_region='A2',
            boxes=36,
            households=28,
            is_valid=True,
        )

        first_payload = self._payload(self.upload_1, self.record_1)
        second_payload = self._payload(upload_2, record_2)

        self.assertEqual(first_payload['pay_basis'], 'households')
        self.assertEqual(int(first_payload['total_pay']), 63000)
        self.assertEqual(first_payload['daily_yongcha_round_count'], 2)
        self.assertEqual(second_payload['pay_basis'], 'households')
        self.assertEqual(int(second_payload['total_pay']), 84000)
        self.assertEqual(second_payload['daily_yongcha_round_count'], 2)

    def test_yongcha_group_base_pay_still_applies_on_multi_round_when_policy_is_off(self):
        self.pay_group.exclude_base_pay_on_multi_round = False
        self.pay_group.save(update_fields=['exclude_base_pay_on_multi_round'])

        upload_2 = DispatchUpload.objects.create(
            team=self.team,
            dispatch_date=self.delivery_date,
            round_no=2,
            status='PENDING',
        )
        record_2 = DispatchRecord.objects.create(
            upload=upload_2,
            row_num=1,
            manager_name=self.crew.code,
            sub_region='A2',
            detail_region='A2',
            boxes=36,
            households=28,
            is_valid=True,
        )

        first_payload = self._payload(self.upload_1, self.record_1)
        second_payload = self._payload(upload_2, record_2)

        self.assertEqual(first_payload['pay_basis'], 'yongcha_pay_group')
        self.assertEqual(int(first_payload['total_pay']), 160000)
        self.assertEqual(first_payload['daily_yongcha_round_count'], 2)
        self.assertEqual(second_payload['pay_basis'], 'yongcha_pay_group')
        self.assertEqual(int(second_payload['total_pay']), 160000)
        self.assertEqual(second_payload['daily_yongcha_round_count'], 2)



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

    def test_operation_report_includes_settlement_amounts_by_date_and_team(self):
        self.client.force_authenticate(user=self.admin)

        delivery_date = date(2026, 5, 14)
        dispatch_upload = DispatchUpload.objects.create(
            uploaded_by=self.team_leader,
            team=self.team_a,
            dispatch_date=delivery_date,
            round_no=1,
            status='CONFIRMED',
        )
        DispatchRecord.objects.create(
            upload=dispatch_upload,
            row_num=1,
            manager_name='driver_a',
            boxes=7,
            households=3,
            is_valid=True,
        )

        confirmed = Settlement.objects.create(
            team=self.team_a,
            period_start=delivery_date,
            period_end=delivery_date,
            status='CONFIRMED',
        )
        paid = Settlement.objects.create(
            team=self.team_a,
            period_start=delivery_date,
            period_end=date(2026, 5, 15),
            status='PAID',
        )
        draft = Settlement.objects.create(
            team=self.team_a,
            period_start=delivery_date,
            period_end=date(2026, 5, 16),
            status='DRAFT',
        )

        SettlementDetail.objects.create(
            settlement=confirmed,
            dispatch_upload=dispatch_upload,
            region='A1',
            delivery_type='SAME_DAY',
            boxes=4,
            receive_amount=1000,
            pay_amount=400,
            profit=600,
            is_yongcha=False,
        )
        SettlementDetail.objects.create(
            settlement=confirmed,
            dispatch_upload=dispatch_upload,
            region='A2',
            delivery_type='SAME_DAY',
            boxes=3,
            receive_amount=2000,
            pay_amount=1500,
            profit=500,
            is_yongcha=True,
        )
        SettlementDetail.objects.create(
            settlement=paid,
            region='A3',
            delivery_type='SAME_DAY',
            boxes=2,
            receive_amount=9000,
            pay_amount=8000,
            profit=1000,
            is_yongcha=True,
        )
        SettlementDetail.objects.create(
            settlement=draft,
            region='A4',
            delivery_type='SAME_DAY',
            boxes=2,
            receive_amount=7000,
            pay_amount=6000,
            profit=1000,
            is_yongcha=False,
        )

        response = self.client.get('/api/v1/dispatch/uploads/operation-report/', {
            'start': delivery_date.isoformat(),
            'end': delivery_date.isoformat(),
            'metric': 'boxes',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = response.data['results'][0]
        self.assertEqual(row['work_date'], delivery_date.isoformat())
        self.assertEqual(row['delivery_date'], delivery_date.isoformat())
        self.assertEqual(row['amount_total_receive'], 12000)
        self.assertEqual(row['amount_regular_pay'], 400)
        self.assertEqual(row['amount_yongcha_pay'], 9500)
        self.assertEqual(row['amount_profit'], 2100)
        self.assertEqual(row['boxes_per_household'], 2.33)
        self.assertEqual(response.data['summary']['amount_total_receive'], 12000)


class OperationReportAmountLookupTests(TestCase):
    def setUp(self):
        self.delivery_date = date(2026, 5, 14)
        self.team_a = Team.objects.create(code='A', name='A team', company_app='cheonha')
        self.team_b = Team.objects.create(code='B', name='B team', company_app='abc')
        self.admin = User.objects.create_user(
            username='amount_admin',
            email='amount_admin@example.com',
            password='testpass123',
            role='ADMIN',
        )
        self.team_leader = User.objects.create_user(
            username='amount_leader',
            email='amount_leader@example.com',
            password='testpass123',
            role='TEAM_LEADER',
            team=self.team_a,
        )

    def _settlement(self, team, status='CONFIRMED', period_end=None):
        return Settlement.objects.create(
            team=team,
            period_start=self.delivery_date,
            period_end=period_end or self.delivery_date,
            status=status,
        )

    def _detail(self, settlement, receive, pay, profit, is_yongcha=False):
        return SettlementDetail.objects.create(
            settlement=settlement,
            region='A1',
            delivery_type='SAME_DAY',
            boxes=1,
            receive_amount=receive,
            pay_amount=pay,
            profit=profit,
            is_yongcha=is_yongcha,
        )

    def test_amount_lookup_matches_dashboard_settlement_detail_formula(self):
        settlement = self._settlement(self.team_a)
        self._detail(settlement, receive=1000, pay=400, profit=600, is_yongcha=False)
        self._detail(settlement, receive=2000, pay=1500, profit=500, is_yongcha=True)
        self._detail(
            self._settlement(self.team_a, status='DRAFT', period_end=date(2026, 5, 15)),
            receive=9000,
            pay=8000,
            profit=1000,
            is_yongcha=True,
        )

        lookup = build_operation_report_amount_lookup(
            start_date=self.delivery_date,
            end_date=self.delivery_date,
            team_ids={self.team_a.id},
            user=self.admin,
            company_app='cheonha',
        )

        self.assertEqual(lookup[(self.delivery_date.isoformat(), self.team_a.id)], {
            'amount_total_receive': 3000,
            'amount_regular_pay': 400,
            'amount_yongcha_pay': 1500,
            'amount_profit': 1100,
        })

    def test_amount_lookup_preserves_company_and_team_scope(self):
        self._detail(self._settlement(self.team_a), receive=1000, pay=400, profit=600)
        self._detail(self._settlement(self.team_b), receive=9000, pay=8000, profit=1000)

        admin_lookup = build_operation_report_amount_lookup(
            start_date=self.delivery_date,
            end_date=self.delivery_date,
            team_ids={self.team_a.id, self.team_b.id},
            user=self.admin,
            company_app='cheonha',
        )
        leader_lookup = build_operation_report_amount_lookup(
            start_date=self.delivery_date,
            end_date=self.delivery_date,
            team_ids={self.team_a.id, self.team_b.id},
            user=self.team_leader,
            company_app='abc',
        )

        self.assertIn((self.delivery_date.isoformat(), self.team_a.id), admin_lookup)
        self.assertNotIn((self.delivery_date.isoformat(), self.team_b.id), admin_lookup)
        self.assertIn((self.delivery_date.isoformat(), self.team_a.id), leader_lookup)
        self.assertNotIn((self.delivery_date.isoformat(), self.team_b.id), leader_lookup)


class OperationReportSummaryTests(TestCase):
    def test_summary_preserves_public_totals_and_backward_compatibility_keys(self):
        rows = [
            {
                'actual_total_boxes': 10,
                'round_1_boxes': 3,
                'round_2_boxes': 4,
                'round_3_boxes': 3,
                'amount_total_receive': 10000,
                'amount_regular_pay': 3000,
                'amount_yongcha_pay': 4000,
                'amount_profit': 3000,
                'round_1_input_count': 1,
                'round_2_input_count': 2,
                'round_3_input_count': 3,
            },
            {
                'actual_total_boxes': 5,
                'round_1_boxes': 2,
                'round_2_boxes': 1,
                'round_3_boxes': 2,
                'amount_total_receive': 5000,
                'amount_regular_pay': 1000,
                'amount_yongcha_pay': 2000,
                'amount_profit': 2000,
                'round_1_input_count': 1,
                'round_2_input_count': 1,
                'round_3_input_count': 1,
            },
        ]

        summary = build_operation_report_summary(rows)

        self.assertEqual(summary['row_count'], 2)
        self.assertEqual(summary['actual_total_boxes'], 15)
        self.assertEqual(summary['total_boxes'], 15)
        self.assertEqual(summary['total_volume'], 15)
        self.assertEqual(summary['round_1_boxes'], 5)
        self.assertEqual(summary['round_2_boxes'], 5)
        self.assertEqual(summary['round_3_boxes'], 5)
        self.assertEqual(summary['amount_total_receive'], 15000)
        self.assertEqual(summary['amount_regular_pay'], 4000)
        self.assertEqual(summary['amount_yongcha_pay'], 6000)
        self.assertEqual(summary['amount_profit'], 5000)
        self.assertEqual(summary['round_1_input_count'], 2)
        self.assertEqual(summary['round_2_input_count'], 3)
        self.assertEqual(summary['round_3_input_count'], 4)

    def test_summary_returns_zeroes_for_empty_rows(self):
        summary = build_operation_report_summary([])

        self.assertEqual(summary['row_count'], 0)
        self.assertEqual(summary['actual_total_boxes'], 0)
        self.assertEqual(summary['total_boxes'], 0)
        self.assertEqual(summary['amount_profit'], 0)


class OperationReportCsvTests(TestCase):
    def test_csv_header_preserves_screen_row_order(self):
        header = build_operation_report_csv_header('박스수', '박스')

        self.assertEqual(header[:9], [
            '날짜(배송일)',
            '요일(배송일)',
            '조',
            '실제 처리 박스수',
            '전체수신(원)',
            '정규지급(원)',
            '용차지급(원)',
            '수익(원)',
            '가구당 박스수',
        ])
        self.assertEqual(header[9:12], ['1회차 박스수', '2회차 박스수', '3회차 박스수'])
        self.assertEqual(header[-4:], ['3회차 투입 대수', '3회차 매니저', '3회차 용차', '3회차 용차비율'])

    def test_csv_row_preserves_public_field_order(self):
        row = {
            'work_date': '2026-05-14',
            'weekday': '목',
            'team_name': 'A조',
            'actual_total_boxes': 10,
            'amount_total_receive': 10000,
            'amount_regular_pay': 3000,
            'amount_yongcha_pay': 4000,
            'amount_profit': 3000,
            'boxes_per_household': 1.25,
            'round_1_boxes': 3,
            'round_2_boxes': 4,
            'round_3_boxes': 3,
            'round_1_productivity': 3,
            'round_3_productivity': 1,
            'multi_round_productivity': 6,
            'round_1_input_count': 1,
            'round_1_manager_count': 1,
            'round_1_yongcha_count': 0,
            'round_1_yongcha_ratio': 0,
            'round_2_input_count': 2,
            'round_2_manager_count': 1,
            'round_2_yongcha_count': 1,
            'round_2_yongcha_ratio': 50,
            'round_3_input_count': 3,
            'round_3_manager_count': 2,
            'round_3_yongcha_count': 1,
            'round_3_yongcha_ratio': 33.33,
        }

        csv_row = build_operation_report_csv_row(row)

        self.assertEqual(csv_row[:9], [
            '2026-05-14',
            '목',
            'A조',
            10,
            10000,
            3000,
            4000,
            3000,
            1.25,
        ])
        self.assertEqual(csv_row[9:12], [3, 4, 3])
        self.assertEqual(csv_row[-4:], [3, 2, 1, 33.33])
