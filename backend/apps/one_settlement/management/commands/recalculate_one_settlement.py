from django.core.management.base import BaseCommand

from apps.one_settlement.services import recalculate_one_month_amounts


class Command(BaseCommand):
    help = "Recalculate stored ONE shipment order amounts for one company/month."

    def add_arguments(self, parser):
        parser.add_argument("--company-app", default="new", help="Company app code. ONE currently allows only new.")
        parser.add_argument("--month", required=True, help="Settlement month in YYYY-MM format.")

    def handle(self, *args, **options):
        result = recalculate_one_month_amounts(
            company_app=options["company_app"],
            month=options["month"],
        )
        self.stdout.write(self.style.SUCCESS(
            "recalculated ONE settlement "
            f"month={result['month']} "
            f"orders={result['order_count']} "
            f"updated={result['updated_count']} "
            f"w12_days={result['w12_daily_volume_days']}"
        ))
