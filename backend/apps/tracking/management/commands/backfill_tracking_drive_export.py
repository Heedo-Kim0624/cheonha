import os
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.tracking.models import TrackingSession
from apps.tracking.services import (
    GOOGLE_APPLICATION_CREDENTIALS_ENV,
    PROCESSED_TRACKING_CSV_EXPORT_DIR_ENV,
    TRACKING_DRIVE_SERVICE_ACCOUNT_FILE_ENV,
    _anonymized_crew_export_code,
    _load_raw_tracking_csv,
    _session_is_allowed_for_tracking_drive_export,
    _tracking_drive_credentials_path,
    export_processed_tracking_csv,
)


class Command(BaseCommand):
    help = "Backfill eligible tracking sessions to the configured local/Google Drive CSV export target."

    def add_arguments(self, parser):
        default_since = timezone.localdate() - timedelta(days=1)
        parser.add_argument(
            "--since",
            default=default_since.isoformat(),
            help="Filter by TrackingSession.created_at from this local date. Default: yesterday.",
        )
        parser.add_argument(
            "--until",
            default=None,
            help="Filter by TrackingSession.created_at through this local date, inclusive.",
        )
        parser.add_argument(
            "--session-id",
            dest="session_ids",
            action="append",
            type=int,
            default=[],
            help="Export a specific TrackingSession id. Can be repeated.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Maximum number of sessions to scan. 0 means no limit.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only show eligible/skipped sessions. Do not write files or upload to Drive.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])
        if not dry_run and not self._has_export_target():
            raise CommandError(
                "No export target is configured. Set "
                f"{PROCESSED_TRACKING_CSV_EXPORT_DIR_ENV} or "
                f"{TRACKING_DRIVE_SERVICE_ACCOUNT_FILE_ENV}/{GOOGLE_APPLICATION_CREDENTIALS_ENV}."
            )

        qs = (
            TrackingSession.objects
            .select_related("crew_member", "crew_member__team", "crew_member__mobile_app_user")
            .order_by("created_at", "id")
        )

        session_ids = options.get("session_ids") or []
        if session_ids:
            qs = qs.filter(id__in=session_ids)
        else:
            since = self._parse_local_date(options["since"], "--since")
            until = self._parse_local_date(options["until"], "--until") if options["until"] else None
            qs = qs.filter(created_at__gte=self._start_of_local_day(since))
            if until:
                qs = qs.filter(created_at__lt=self._start_of_local_day(until + timedelta(days=1)))

        limit = int(options.get("limit") or 0)
        if limit > 0:
            qs = qs[:limit]

        scanned = eligible = exported = skipped = failed = 0
        self.stdout.write("Tracking Drive export backfill")
        self.stdout.write(f"mode: {'dry-run' if dry_run else 'export'}")

        for session in qs:
            scanned += 1
            anon = _anonymized_crew_export_code(session.crew_member)
            label = (
                f"session={session.id} anon={anon} "
                f"created_at={timezone.localtime(session.created_at):%Y-%m-%d %H:%M:%S} "
                f"session_date={session.session_date} app_version={session.app_version or '-'}"
            )
            reason = self._skip_reason(session)
            if reason:
                skipped += 1
                self.stdout.write(f"SKIP {label} reason={reason}")
                continue

            eligible += 1
            if dry_run:
                self.stdout.write(f"OK   {label}")
                continue

            try:
                target = export_processed_tracking_csv(session)
            except Exception as exc:
                failed += 1
                self.stderr.write(f"FAIL {label} error={type(exc).__name__}: {exc}")
                continue

            if target:
                exported += 1
                self.stdout.write(self.style.SUCCESS(f"DONE {label} target={target}"))
            else:
                skipped += 1
                self.stdout.write(f"SKIP {label} reason=export_returned_empty")

        self.stdout.write(
            self.style.SUCCESS(
                "summary: "
                f"scanned={scanned}, eligible={eligible}, exported={exported}, "
                f"skipped={skipped}, failed={failed}"
            )
        )

    def _has_export_target(self) -> bool:
        return bool(
            os.environ.get(PROCESSED_TRACKING_CSV_EXPORT_DIR_ENV, "").strip()
            or _tracking_drive_credentials_path()
        )

    def _skip_reason(self, session: TrackingSession) -> str:
        if not _session_is_allowed_for_tracking_drive_export(session):
            return "policy_or_app_version_not_allowed"
        if not _load_raw_tracking_csv(session):
            return "raw_csv_missing"
        return ""

    def _parse_local_date(self, value: str, option_name: str):
        try:
            return datetime.strptime(str(value), "%Y-%m-%d").date()
        except ValueError as exc:
            raise CommandError(f"{option_name} must be YYYY-MM-DD: {value}") from exc

    def _start_of_local_day(self, value):
        local_tz = timezone.get_current_timezone()
        naive = datetime.combine(value, time.min)
        return timezone.make_aware(naive, local_tz)
