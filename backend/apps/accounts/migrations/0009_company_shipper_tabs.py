from django.db import migrations, models


DEFAULT_COMPANY_TABS = ["dispatch", "crew", "region"]
ALL_COMPANY_TABS = [
    "dispatch",
    "crew",
    "region",
    "dashboard",
    "operations",
    "settlement",
    "inquiry",
    "tracking",
    "manpower",
]


def _clean_tabs(tabs):
    cleaned = []
    for tab in tabs or []:
        if tab in ALL_COMPANY_TABS and tab not in cleaned:
            cleaned.append(tab)
    return cleaned


def seed_company_shipper_tabs(apps, schema_editor):
    CompanyApp = apps.get_model("accounts", "CompanyApp")
    Shipper = apps.get_model("accounts", "Shipper")
    shippers = {shipper.code: shipper for shipper in Shipper.objects.all()}

    for company in CompanyApp.objects.all():
        enabled_shippers = list(company.enabled_shippers or ["kurly"])
        existing = company.enabled_shipper_tabs or {}
        next_map = {}

        for code in enabled_shippers:
            configured = existing.get(code)
            if configured is None:
                shipper = shippers.get(code)
                configured = getattr(shipper, "default_enabled_tabs", None) or []
            if not configured:
                configured = ["settlement"] if code == "one" else (company.enabled_tabs or DEFAULT_COMPANY_TABS)

            available = _clean_tabs(getattr(shippers.get(code), "available_tabs", None) or ALL_COMPANY_TABS)
            tabs = [tab for tab in _clean_tabs(configured) if not available or tab in available]
            if not tabs:
                tabs = ["settlement"] if code == "one" else list(DEFAULT_COMPANY_TABS)
                tabs = [tab for tab in tabs if not available or tab in available]
            next_map[code] = tabs

        union_tabs = []
        for tabs in next_map.values():
            for tab in tabs:
                if tab not in union_tabs:
                    union_tabs.append(tab)

        company.enabled_shipper_tabs = next_map
        company.enabled_tabs = union_tabs or list(DEFAULT_COMPANY_TABS)
        company.save(update_fields=["enabled_shipper_tabs", "enabled_tabs", "updated_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_shipper_box_rate_adjustment"),
    ]

    operations = [
        migrations.AddField(
            model_name="companyapp",
            name="enabled_shipper_tabs",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.RunPython(seed_company_shipper_tabs, migrations.RunPython.noop),
    ]
