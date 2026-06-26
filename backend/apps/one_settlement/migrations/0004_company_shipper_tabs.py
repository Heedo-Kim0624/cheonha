from django.db import migrations


def sync_one_company_shipper_tabs(apps, schema_editor):
    CompanyApp = apps.get_model("accounts", "CompanyApp")

    for company in CompanyApp.objects.filter(code="new"):
        enabled_shippers = list(company.enabled_shippers or [])
        if "one" not in enabled_shippers:
            enabled_shippers.append("one")

        shipper_tabs = dict(getattr(company, "enabled_shipper_tabs", None) or {})
        shipper_tabs["one"] = ["settlement"]

        union_tabs = []
        for tabs in shipper_tabs.values():
            for tab in tabs or []:
                if tab not in union_tabs:
                    union_tabs.append(tab)

        company.enabled_shippers = enabled_shippers
        company.enabled_shipper_tabs = shipper_tabs
        company.enabled_tabs = union_tabs or ["settlement"]
        company.save(update_fields=["enabled_shippers", "enabled_shipper_tabs", "enabled_tabs", "updated_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0009_company_shipper_tabs"),
        ("one_settlement", "0003_collection_index"),
    ]

    operations = [
        migrations.RunPython(sync_one_company_shipper_tabs, migrations.RunPython.noop),
    ]
