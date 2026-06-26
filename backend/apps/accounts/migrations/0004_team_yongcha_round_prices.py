from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_team_company_app"),
    ]

    operations = [
        migrations.AddField(
            model_name="team",
            name="yongcha_round_1_pay_price",
            field=models.DecimalField(
                decimal_places=0,
                default=3000,
                help_text="Household-based pay rate for yongcha drivers on round 1.",
                max_digits=12,
                verbose_name="Yongcha round 1 pay price",
            ),
        ),
        migrations.AddField(
            model_name="team",
            name="yongcha_round_2_pay_price",
            field=models.DecimalField(
                decimal_places=0,
                default=3000,
                help_text="Household-based pay rate for yongcha drivers on round 2.",
                max_digits=12,
                verbose_name="Yongcha round 2 pay price",
            ),
        ),
        migrations.AddField(
            model_name="team",
            name="yongcha_round_3_pay_price",
            field=models.DecimalField(
                decimal_places=0,
                default=3000,
                help_text="Household-based pay rate for yongcha drivers on round 3.",
                max_digits=12,
                verbose_name="Yongcha round 3 pay price",
            ),
        ),
    ]
