from django.db import migrations, models
import django.db.models.deletion


def seed_legal_document_versions(apps, schema_editor):
    LegalDocumentVersionLog = apps.get_model("mobile", "LegalDocumentVersionLog")
    rows = [
        ("web_terms", "WEB", "CLEVER 관리자 회원 서비스 이용약관", "2026-06-04", "/terms/", "260604 CLEVER 관리자 회원 서비스 이용약관.docx"),
        ("app_terms", "APP", "CLEVER 배송원 회원 서비스 이용약관", "2026-06-04", "/driver-terms/", "260604 CLEVER 배송원 회원 서비스 이용약관.docx"),
        ("privacy_policy", "WEB/APP", "개인정보 처리방침", "2026-06-04", "/privacy/", "260604 이브이앤솔루션 개인정보 처리방침.docx"),
        ("location_terms", "WEB/APP", "위치기반서비스 이용약관", "2026-06-04", "/location-terms/", "260604 이브이앤솔루션 위치기반서비스 이용약관.docx"),
        ("data_processing", "WEB/APP", "제3자 정보제공 동의", "2026-06-04", "/data-processing/", "260604 이브이앤솔루션 개인정보 처리방침.docx"),
        ("marketing_consent", "WEB/APP", "마케팅 및 이벤트 정보 수신 동의", "2026-06-04", "/marketing-consent/", "260604 이브이앤솔루션 개인정보 처리방침.docx"),
    ]
    for document_key, audience, title, version, public_url, source_filename in rows:
        LegalDocumentVersionLog.objects.get_or_create(
            document_key=document_key,
            version=version,
            defaults={
                "audience": audience,
                "title": title,
                "public_url": public_url,
                "source_filename": source_filename,
                "effective_date": "2026-06-04",
                "change_note": "260604 이용약관 및 개인정보처리방침 최종본 반영",
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_shipper_box_rate_adjustment"),
        ("mobile", "0007_mobileappuser_last_app_version"),
    ]

    operations = [
        migrations.CreateModel(
            name="LegalDocumentVersionLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("document_key", models.CharField(db_index=True, max_length=50)),
                ("audience", models.CharField(db_index=True, max_length=20)),
                ("title", models.CharField(max_length=200)),
                ("version", models.CharField(db_index=True, max_length=20)),
                ("public_url", models.CharField(max_length=255)),
                ("source_filename", models.CharField(blank=True, max_length=255)),
                ("effective_date", models.DateField()),
                ("change_note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "legal_document_version_logs",
                "ordering": ["-effective_date", "document_key"],
                "unique_together": {("document_key", "version")},
            },
        ),
        migrations.CreateModel(
            name="LegalConsentHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("subject_type", models.CharField(choices=[("MOBILE_USER", "Mobile user"), ("COMPANY_APP", "Company app")], db_index=True, max_length=20)),
                ("subject_identifier", models.CharField(db_index=True, max_length=120)),
                ("agreement_key", models.CharField(db_index=True, max_length=60)),
                ("document_key", models.CharField(db_index=True, max_length=50)),
                ("document_version", models.CharField(db_index=True, max_length=20)),
                ("agreed", models.BooleanField(default=True)),
                ("agreed_at", models.DateTimeField(db_index=True)),
                ("app_version", models.CharField(blank=True, max_length=40)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("company_app", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="legal_consent_histories", to="accounts.companyapp")),
                ("mobile_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="legal_consent_histories", to="mobile.mobileappuser")),
            ],
            options={
                "db_table": "legal_consent_histories",
                "ordering": ["-agreed_at", "-id"],
            },
        ),
        migrations.RunPython(seed_legal_document_versions, migrations.RunPython.noop),
    ]
