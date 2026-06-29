from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Sum

from apps.crew.models import CrewMember, OvertimeSetting
from apps.dispatch.models import DispatchUpload
from apps.dispatch.settlement_services import is_effective_yongcha, replace_settlement_details_for_crew_upload
from apps.settlement.models import SettlementDetail


class Command(BaseCommand):
    help = 'Rebuild settlement details using round-based yongcha rules and household-based yongcha pay.'

    def _refresh_settlement_totals(self, settlement_ids):
        for settlement_id in settlement_ids:
            settlement = SettlementDetail.objects.filter(settlement_id=settlement_id).values(
                'settlement_id'
            ).annotate(
                receive=Sum('receive_amount'),
                pay=Sum('pay_amount'),
                overtime=Sum('overtime_cost'),
                other=Sum('other_cost'),
                profit=Sum('profit'),
            ).order_by('settlement_id').first()
            if not settlement:
                continue
            from apps.settlement.models import Settlement
            Settlement.objects.filter(id=settlement_id).update(
                total_receive=settlement['receive'] or 0,
                total_pay=settlement['pay'] or 0,
                total_overtime=settlement['overtime'] or 0,
                total_other_cost=settlement['other'] or 0,
                total_profit=settlement['profit'] or 0,
            )

    def _refresh_upload_summaries(self, upload_ids):
        for upload in DispatchUpload.objects.filter(id__in=upload_ids).prefetch_related('records').select_related('team'):
            records = [record for record in upload.records.all() if record.is_valid and int(record.boxes or 0) > 0]
            crew_names = {
                str(record.manager_name or '').strip()
                for record in records
                if str(record.manager_name or '').strip()
            }
            regular_count = 0
            yongcha_count = 0
            for name in crew_names:
                explicit_yongcha = any(
                    str(record.manager_name or '').strip() == name and record.is_yongcha
                    for record in records
                )
                crew = CrewMember.objects.filter(team=upload.team, code=name).first() if upload.team_id else None
                if not crew:
                    crew = CrewMember.objects.filter(code=name).first()
                if is_effective_yongcha(crew, round_no=upload.round_no, explicit_yongcha=explicit_yongcha):
                    yongcha_count += 1
                else:
                    regular_count += 1
            upload.mor_total_boxes = sum(int(record.boxes or 0) for record in records)
            upload.mor_regular_crew_count = regular_count
            upload.mor_yongcha_crew_count = yongcha_count
            upload.save(update_fields=[
                'mor_total_boxes',
                'mor_regular_crew_count',
                'mor_yongcha_crew_count',
                'updated_at',
            ])

    def handle(self, *args, **options):
        detail_groups = {}
        queryset = SettlementDetail.objects.exclude(dispatch_upload=None).exclude(crew_member=None).select_related(
            'settlement', 'dispatch_upload', 'crew_member', 'dispatch_upload__team'
        )
        for detail in queryset.iterator():
            key = (detail.settlement_id, detail.dispatch_upload_id, detail.crew_member_id)
            detail_groups[key] = (detail.settlement, detail.dispatch_upload, detail.crew_member)

        settlement_ids = set()
        upload_ids = set()
        rebuilt = 0
        for settlement, dispatch_upload, crew_member in detail_groups.values():
            matching_records = list(
                dispatch_upload.records.filter(
                    is_valid=True,
                    manager_name__in=[name for name in {crew_member.code, crew_member.name} if name],
                )
            )
            overtime_setting = OvertimeSetting.objects.filter(
                dispatch_upload=dispatch_upload,
                crew_member=crew_member,
                is_overtime=True,
            ).first()
            overtime_cost = Decimal(str(overtime_setting.overtime_cost or 0)) if overtime_setting else Decimal('0')
            receive_price = Decimal(str(dispatch_upload.team.receive_price if dispatch_upload.team else 0))
            replace_settlement_details_for_crew_upload(
                settlement=settlement,
                crew_member=crew_member,
                dispatch_upload=dispatch_upload,
                records=matching_records,
                receive_price=receive_price,
                overtime_cost=overtime_cost,
            )
            settlement_ids.add(settlement.id)
            upload_ids.add(dispatch_upload.id)
            rebuilt += 1

        self._refresh_settlement_totals(settlement_ids)
        self._refresh_upload_summaries(upload_ids)
        self.stdout.write(self.style.SUCCESS(
            f'rebuilt {rebuilt} crew/upload settlement groups, '
            f'{len(settlement_ids)} settlements, {len(upload_ids)} uploads'
        ))
