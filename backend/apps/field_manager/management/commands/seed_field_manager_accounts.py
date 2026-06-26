from collections import OrderedDict
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.vehicle_management.models import Company
from apps.field_manager.models import (
    FieldManagerAccount,
    FieldManagerSession,
    normalize_phone,
)


class Command(BaseCommand):
    help = '최근 현장관리자 로그인 세션을 FieldManagerAccount 허용목록으로 변환합니다.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=3650, help='최근 N일 로그인 세션을 기준으로 합니다.')
        parser.add_argument('--company', default='', help='특정 회사 코드만 처리합니다. 예: CHEONHA')
        parser.add_argument('--apply', action='store_true', help='실제 계정을 생성합니다. 없으면 dry-run입니다.')

    def handle(self, *args, **options):
        since = timezone.now() - timedelta(days=options['days'])
        company_filter = str(options.get('company') or '').strip().upper()
        sessions = FieldManagerSession.objects.filter(logged_in_at__gte=since).order_by('-logged_in_at')
        if company_filter:
            sessions = sessions.filter(company_code=company_filter)

        candidates = OrderedDict()
        company_codes = set(Company.objects.filter(is_active=True).values_list('code', flat=True))
        for session in sessions:
            company_code = str(session.company_code or '').strip().upper()
            team_code = str(session.team_code or '').strip().upper()
            phone = normalize_phone(session.phone)
            if not company_code or not team_code or not phone or company_code not in company_codes:
                continue
            key = (company_code, team_code, phone)
            if key not in candidates:
                candidates[key] = {
                    'company_code': company_code,
                    'team_code': team_code,
                    'phone': phone,
                    'display_phone': session.phone or phone,
                    'latest_login_at': session.logged_in_at,
                }

        existing = set(
            FieldManagerAccount.objects.select_related('company')
            .values_list('company__code', 'team_code', 'phone')
        )
        to_create = [value for key, value in candidates.items() if key not in existing]

        self.stdout.write(
            f'candidates={len(candidates)} existing={len(candidates) - len(to_create)} '
            f'to_create={len(to_create)} apply={options["apply"]}'
        )
        for item in to_create[:20]:
            self.stdout.write(
                f'  + {item["company_code"]} {item["team_code"]} {item["display_phone"]}'
            )
        if len(to_create) > 20:
            self.stdout.write(f'  ... {len(to_create) - 20} more')

        if not options['apply']:
            self.stdout.write(self.style.WARNING('dry-run only. 실제 생성하려면 --apply를 사용하세요.'))
            return

        company_map = {company.code: company for company in Company.objects.filter(is_active=True)}
        with transaction.atomic():
            for item in to_create:
                FieldManagerAccount.objects.create(
                    company=company_map[item['company_code']],
                    team_code=item['team_code'],
                    phone=item['phone'],
                    display_phone=item['display_phone'],
                    memo='seeded from FieldManagerSession',
                    last_login_at=item['latest_login_at'],
                )
        self.stdout.write(self.style.SUCCESS(f'created={len(to_create)}'))
