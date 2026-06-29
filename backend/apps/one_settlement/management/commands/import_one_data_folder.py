from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.one_settlement.constants import SHIPPER_CODE
from apps.one_settlement.models import OneDriverStatementOverride, OneSettlementUpload
from apps.one_settlement.services import ensure_one_company_access, import_one_file


class Command(BaseCommand):
    help = "Import a folder of ONE settlement xlsx files into the isolated ONE settlement tables."

    def add_arguments(self, parser):
        parser.add_argument("root", help="Folder containing ONE xlsx files.")
        parser.add_argument("--company-app", default="new", help="Company app code. ONE currently allows only new.")
        parser.add_argument(
            "--clear-month",
            default="",
            help="Delete existing ONE uploads and statement overrides for this YYYY-MM month before importing.",
        )

    def handle(self, *args, **options):
        company_app = ensure_one_company_access(options["company_app"])
        root = Path(options["root"]).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise CommandError(f"Folder does not exist: {root}")

        clear_month = str(options.get("clear_month") or "").strip()
        if clear_month:
            with transaction.atomic():
                upload_deleted, _ = OneSettlementUpload.objects.filter(
                    company_app=company_app,
                    shipper_code=SHIPPER_CODE,
                    month=clear_month,
                ).delete()
                override_deleted, _ = OneDriverStatementOverride.objects.filter(
                    company_app=company_app,
                    shipper_code=SHIPPER_CODE,
                    month=clear_month,
                ).delete()
            self.stdout.write(
                self.style.WARNING(
                    f"cleared month={clear_month}: uploads/orders={upload_deleted}, overrides={override_deleted}"
                )
            )

        files = sorted(path for path in root.rglob("*.xlsx") if path.is_file())
        if not files:
            raise CommandError(f"No xlsx files found under {root}")

        imported = 0
        duplicate = 0
        failed = 0
        for path in files:
            rel_name = str(path.relative_to(root)).replace("\\", "/")
            try:
                with path.open("rb") as handle:
                    result = import_one_file(
                        company_app=company_app,
                        uploaded_by=None,
                        uploaded_file=File(handle, name=rel_name),
                    )
                if result["duplicate"]:
                    duplicate += 1
                    status = "DUP"
                else:
                    imported += 1
                    status = "OK"
                self.stdout.write(f"{status} {rel_name}")
            except Exception as exc:
                failed += 1
                self.stdout.write(self.style.ERROR(f"FAIL {rel_name}: {exc}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"done files={len(files)} imported={imported} duplicate={duplicate} failed={failed}"
            )
        )
