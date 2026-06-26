import json
from datetime import date
from pathlib import Path

from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.accounts.models import Team
from apps.common.company_scope import DEFAULT_COMPANY_APP, normalize_company_app
from apps.region.models import Region, RegionPrice
from apps.territory.models import Territory, extract_group_letter


class Command(BaseCommand):
    help = "Import X territory polygons from the bundled GPKG-derived fixture."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            default="",
            help="Optional fixture JSON path. Defaults to territory/fixtures/x_territories.json.",
        )
        parser.add_argument(
            "--company-app",
            default=DEFAULT_COMPANY_APP,
            help="Company app code for the X team. Defaults to cheonha.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete existing X territories for the company that are not in the fixture.",
        )

    def handle(self, *args, **options):
        fixture = options.get("fixture")
        fixture_path = Path(fixture) if fixture else Path(__file__).resolve().parents[2] / "fixtures" / "x_territories.json"
        company_app = normalize_company_app(options.get("company_app"))
        group = "X"

        if not fixture_path.exists():
            raise SystemExit(f"Fixture not found: {fixture_path}")

        rows = json.loads(fixture_path.read_text(encoding="utf-8"))
        rows = [row for row in rows if extract_group_letter(str(row.get("code") or "")) == group]
        codes = {str(row.get("code") or "").strip().upper() for row in rows if str(row.get("code") or "").strip()}

        created = 0
        updated = 0
        deleted = 0

        with transaction.atomic():
            team, _ = Team.objects.get_or_create(
                code=group,
                company_app=company_app,
                defaults={"name": f"{group}\uc870", "is_active": True},
            )
            update_fields = []
            if not team.name:
                team.name = f"{group}\uc870"
                update_fields.append("name")
            if not team.is_active:
                team.is_active = True
                update_fields.append("is_active")
            if update_fields:
                team.save(update_fields=update_fields)

            if options.get("replace"):
                deleted, _ = (
                    Territory.objects
                    .filter(group_letter=group)
                    .filter(Q(team=team) | Q(team__isnull=True) | Q(team__company_app=company_app))
                    .exclude(code__in=codes)
                    .delete()
                )

            for item in rows:
                code = str(item.get("code") or "").strip().upper()
                if not code:
                    continue

                territory, was_created = Territory.objects.update_or_create(
                    code=code,
                    defaults={
                        "team": team,
                        "geometry": item.get("geometry") or {},
                        "color": item.get("color") or "#2563EB",
                        "note": "X GPKG imported territory",
                    },
                )
                region, _ = Region.objects.update_or_create(
                    code=territory.code,
                    defaults={"team": team, "name": territory.code, "is_active": True},
                )
                RegionPrice.objects.get_or_create(
                    region=region,
                    delivery_type="SAME_DAY",
                    start_date=date(2026, 1, 1),
                    defaults={
                        "receive_price": team.receive_price or 0,
                        "pay_price": team.pay_price or 0,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported X territories: created={created}, updated={updated}, deleted={deleted}, company_app={company_app}"
            )
        )
