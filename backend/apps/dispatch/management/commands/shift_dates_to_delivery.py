from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.dispatch.models import DispatchUpload
from apps.inquiry.models import SettlementInquiry
from apps.settlement.models import Settlement


class Command(BaseCommand):
    help = "Shift existing dispatch/settlement dates from work date to delivery date."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually update dates. Without this flag the command is a dry run.",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=1,
            help="Number of days to shift. Defaults to 1.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        if days == 0:
            raise CommandError("--days must not be 0")

        delta = timedelta(days=days)
        apply_changes = bool(options["apply"])

        uploads = DispatchUpload.objects.exclude(dispatch_date__isnull=True).order_by("-dispatch_date", "-id")
        settlements = Settlement.objects.exclude(period_start__isnull=True).order_by("-period_start", "-id")
        inquiries = SettlementInquiry.objects.exclude(dispatch_date__isnull=True).order_by("-dispatch_date", "-id")

        self.stdout.write(
            f"{'APPLY' if apply_changes else 'DRY RUN'}: shift by {days} day(s) "
            f"uploads={uploads.count()}, settlements={settlements.count()}, inquiries={inquiries.count()}"
        )

        if not apply_changes:
            return

        with transaction.atomic():
            for upload in uploads:
                upload.dispatch_date = upload.dispatch_date + delta
                upload.save(update_fields=["dispatch_date", "updated_at"])

            for settlement in settlements:
                settlement.period_start = settlement.period_start + delta
                settlement.period_end = settlement.period_end + delta
                settlement.save(update_fields=["period_start", "period_end", "updated_at"])

            for inquiry in inquiries:
                inquiry.dispatch_date = inquiry.dispatch_date + delta
                inquiry.save(update_fields=["dispatch_date", "updated_at"])

        self.stdout.write(self.style.SUCCESS("Date shift completed."))
