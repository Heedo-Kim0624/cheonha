from django.core.management.base import BaseCommand, CommandError

from apps.vehicle_management.services.evdash_service import check_evdash_connection


class Command(BaseCommand):
    help = 'EV Dashboard readonly DB 연결과 view 집계를 확인합니다.'

    def handle(self, *args, **options):
        try:
            result = check_evdash_connection()
        except Exception as exc:
            raise CommandError(f'EV Dashboard 연결 실패: {exc.__class__.__name__}: {exc}') from exc

        if not result.get('ok'):
            raise CommandError(result.get('detail') or 'EV Dashboard 연결 실패')

        self.stdout.write(self.style.SUCCESS('EV Dashboard connected OK'))
        self.stdout.write(f'vehicles    : {result.get("vehicles")}')
        self.stdout.write(f'latest      : {result.get("latest")}')
        self.stdout.write(f'fleets      : {result.get("fleets")}')
        self.stdout.write(f'most_recent : {result.get("last_seen")}')
