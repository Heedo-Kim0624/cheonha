from django.db import migrations, models


def mark_ts_groups(apps, schema_editor):
    YongchaPayGroup = apps.get_model("crew", "YongchaPayGroup")
    YongchaPayGroup.objects.filter(name__icontains="TS").update(
        exclude_base_pay_on_multi_round=True
    )


def unmark_ts_groups(apps, schema_editor):
    YongchaPayGroup = apps.get_model("crew", "YongchaPayGroup")
    YongchaPayGroup.objects.filter(name__icontains="TS").update(
        exclude_base_pay_on_multi_round=False
    )


class Migration(migrations.Migration):
    dependencies = [
        ("crew", "0004_yongcha_pay_group_and_regular_fixed_pay"),
    ]

    operations = [
        migrations.AddField(
            model_name="yongchapaygroup",
            name="exclude_base_pay_on_multi_round",
            field=models.BooleanField(
                default=False,
                help_text="체크 시 같은 날 여러 용차 회차를 수행하면 기본급 없이 추가 착당 단가만 적용합니다.",
            ),
        ),
        migrations.RunPython(mark_ts_groups, unmark_ts_groups),
    ]
