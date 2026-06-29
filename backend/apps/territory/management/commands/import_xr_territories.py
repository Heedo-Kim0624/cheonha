import json
from datetime import date
from pathlib import Path

from django.core.management import BaseCommand
from django.db import transaction

from apps.accounts.models import Team
from apps.region.models import Region, RegionPrice
from apps.territory.models import Territory, extract_group_letter


class Command(BaseCommand):
    help = "Import X/R territory polygons from the bundled GPKG-derived fixture."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            default="",
            help="Optional fixture JSON path. Defaults to territory/fixtures/xr_territories.json.",
        )

    def handle(self, *args, **options):
        fixture = options.get("fixture")
        if fixture:
            fixture_path = Path(fixture)
        else:
            fixture_path = Path(__file__).resolve().parents[2] / "fixtures" / "xr_territories.json"

        if not fixture_path.exists():
            raise SystemExit(f"Fixture not found: {fixture_path}")

        rows = json.loads(fixture_path.read_text(encoding="utf-8"))
        created = 0
        updated = 0

        with transaction.atomic():
            teams = {}
            for code in ("X", "R"):
                team, _ = Team.objects.get_or_create(
                    code=code,
                    defaults={"name": f"{code}조", "is_active": True},
                )
                teams[code] = team

            for item in rows:
                code = str(item.get("code") or "").strip()
                if not code:
                    continue
                group = extract_group_letter(code)
                if group not in teams:
                    continue
                team = teams[group]
                defaults = {
                    "team": team,
                    "geometry": item.get("geometry") or {},
                    "color": item.get("color") or ("#2563EB" if group == "X" else "#EC4899"),
                    "note": "R/X GPKG 기반 권역",
                }
                territory, was_created = Territory.objects.update_or_create(
                    code=code,
                    defaults=defaults,
                )
                region, _ = Region.objects.update_or_create(
                    code=territory.code,
                    team=team,
                    defaults={"name": territory.code, "is_active": True},
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

        self.stdout.write(self.style.SUCCESS(f"Imported X/R territories: created={created}, updated={updated}"))
