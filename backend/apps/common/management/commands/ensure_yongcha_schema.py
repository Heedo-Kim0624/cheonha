from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection
from pathlib import Path


class Command(BaseCommand):
    help = "Patch legacy syncdb tables for recently added operational columns."

    FIELDS = (
        ("accounts", "Team", "yongcha_round_1_pay_price"),
        ("accounts", "Team", "yongcha_round_2_pay_price"),
        ("accounts", "Team", "yongcha_round_3_pay_price"),
        ("crew", "CrewMember", "is_yongcha"),
        ("crew", "CrewMember", "yongcha_pay_price"),
        ("crew", "CrewMember", "personal_round_1_yongcha_pay_price"),
        ("crew", "CrewMember", "personal_round_2_yongcha_pay_price"),
        ("crew", "CrewMember", "personal_round_3_yongcha_pay_price"),
        ("crew", "CrewMember", "round_1_is_yongcha"),
        ("crew", "CrewMember", "round_2_is_yongcha"),
        ("crew", "CrewMember", "round_3_is_yongcha"),
        ("crew", "YongchaPayGroup", "exclude_base_pay_on_multi_round"),
        ("crew", "CrewMember", "bank_name"),
        ("crew", "CrewMember", "bank_account_number"),
        ("crew", "CrewMember", "bank_account_holder"),
        ("crew", "CrewMember", "vehicle_inspection_date"),
        ("dispatch", "DispatchUpload", "source_date"),
        ("dispatch", "DispatchUpload", "dispatch_time"),
        ("dispatch", "DispatchUpload", "round_no"),
        ("dispatch", "DispatchUpload", "mor_total_boxes"),
        ("dispatch", "DispatchUpload", "mor_regular_crew_count"),
        ("dispatch", "DispatchUpload", "mor_yongcha_crew_count"),
        ("dispatch", "DispatchRecord", "is_yongcha"),
        ("settlement", "SettlementDetail", "is_yongcha"),
    )

    def handle(self, *args, **options):
        existing_tables = set(connection.introspection.table_names())
        added = []
        skipped = []

        for app_label, model_name, field_name in self.FIELDS:
            model = apps.get_model(app_label, model_name)
            table_name = model._meta.db_table
            if table_name not in existing_tables:
                skipped.append(f"{table_name}.{field_name}: table missing")
                continue

            columns = {
                column.name
                for column in connection.introspection.get_table_description(
                    connection.cursor(), table_name
                )
            }
            if field_name in columns:
                skipped.append(f"{table_name}.{field_name}: exists")
                continue

            field = model._meta.get_field(field_name)
            with connection.schema_editor() as schema_editor:
                schema_editor.add_field(model, field)
            added.append(f"{table_name}.{field_name}")

        if added:
            self.stdout.write(self.style.SUCCESS(f"Added columns: {', '.join(added)}"))
        if skipped:
            self.stdout.write(f"Skipped: {', '.join(skipped)}")

        self._mark_existing_v_suffix_as_yongcha()
        self._backfill_dispatch_upload_metadata()

    def _mark_existing_v_suffix_as_yongcha(self):
        from apps.crew.models import CrewMember
        from apps.dispatch.models import DispatchRecord
        from apps.settlement.models import SettlementDetail

        suffixes = ("v", "V")
        crew_updates = 0
        dispatch_updates = 0

        for crew in CrewMember.objects.filter(is_yongcha=False):
            raw_name = str(crew.name or "").strip()
            raw_code = str(crew.code or "").strip()
            if not (raw_name.endswith(suffixes) or raw_code.endswith(suffixes)):
                continue

            clean_name = raw_name[:-1].strip() if raw_name.endswith(suffixes) else raw_name
            clean_code = raw_code[:-1].strip() if raw_code.endswith(suffixes) else raw_code

            update_fields = ["is_yongcha", "is_new"]
            crew.is_yongcha = True
            crew.is_new = False
            if clean_name and clean_name != crew.name:
                crew.name = clean_name
                update_fields.append("name")
            if clean_code and clean_code != crew.code:
                exists = CrewMember.objects.filter(
                    code=clean_code,
                    team=crew.team,
                ).exclude(pk=crew.pk).exists()
                if not exists:
                    crew.code = clean_code
                    update_fields.append("code")
            crew.save(update_fields=sorted(set(update_fields)))
            SettlementDetail.objects.filter(crew_member=crew).update(is_yongcha=True)
            crew_updates += 1

        for rec in DispatchRecord.objects.filter(is_yongcha=False):
            manager_name = str(rec.manager_name or "").strip()
            if not manager_name.endswith(suffixes):
                continue
            rec.manager_name = manager_name[:-1].strip()
            rec.is_yongcha = True
            rec.save(update_fields=["manager_name", "is_yongcha"])
            dispatch_updates += 1

        if crew_updates or dispatch_updates:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Marked v-suffix yongcha rows: crew={crew_updates}, dispatch={dispatch_updates}"
                )
            )

    def _backfill_dispatch_upload_metadata(self):
        from apps.dispatch.models import DispatchUpload
        from apps.dispatch.views import DispatchUploadViewSet, parse_dispatch_filename_info

        metadata_updates = 0
        summary_updates = 0
        viewset = DispatchUploadViewSet()

        for upload in DispatchUpload.objects.all().iterator():
            filename = upload.original_filename or Path(str(upload.file.name or "")).name
            info = parse_dispatch_filename_info(filename)
            update_fields = []

            for field_name in ("source_date", "dispatch_date", "dispatch_time", "round_no"):
                if getattr(upload, field_name) is None and info.get(field_name) is not None:
                    setattr(upload, field_name, info[field_name])
                    update_fields.append(field_name)

            if update_fields:
                upload.save(update_fields=sorted(set(update_fields)))
                metadata_updates += 1

            try:
                viewset._update_mor_summary(upload)
                summary_updates += 1
            except Exception as exc:
                self.stdout.write(f"Skipped MOR summary for upload {upload.pk}: {exc}")

        if metadata_updates or summary_updates:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Backfilled dispatch metadata={metadata_updates}, mor_summary={summary_updates}"
                )
            )
