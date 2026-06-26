from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.tracking.services import (
    GOOGLE_APPLICATION_CREDENTIALS_ENV,
    TRACKING_DRIVE_SERVICE_ACCOUNT_FILE_ENV,
    _tracking_drive_credentials_path,
    _tracking_drive_folder_id,
    _upload_csv_to_google_drive,
)


class Command(BaseCommand):
    help = "Upload a small test CSV to the configured tracking Google Drive folder."

    def handle(self, *args, **options):
        folder_id = _tracking_drive_folder_id()
        credentials_path = _tracking_drive_credentials_path()
        if not credentials_path:
            raise CommandError(
                "Google Drive credentials are not configured. Set "
                f"{TRACKING_DRIVE_SERVICE_ACCOUNT_FILE_ENV} or {GOOGLE_APPLICATION_CREDENTIALS_ENV}."
            )

        filename = f"tracking_drive_export_test_{timezone.localtime():%Y%m%d_%H%M%S}.csv"
        content = "time,name,state\n" f"{timezone.localtime():%Y-%m-%d %H:%M:%S},drive-export-test,OK\n"
        uploaded = _upload_csv_to_google_drive(filename, content)

        self.stdout.write(self.style.SUCCESS("Google Drive export test uploaded."))
        self.stdout.write(f"folder_id: {folder_id}")
        self.stdout.write(f"file: {filename}")
        self.stdout.write(f"target: {uploaded}")
