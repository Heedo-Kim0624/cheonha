from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crew", "0002_round_yongcha_and_household_rate"),
    ]

    operations = [
        migrations.AddField(
            model_name="crewmember",
            name="personal_round_1_yongcha_pay_price",
            field=models.DecimalField(
                decimal_places=0,
                default=0,
                help_text="개별 배송원의 1회차 용차 지급단가 override 값",
                max_digits=12,
                verbose_name="1회차 개인 용차 지급단가(가구당)",
            ),
        ),
        migrations.AddField(
            model_name="crewmember",
            name="personal_round_2_yongcha_pay_price",
            field=models.DecimalField(
                decimal_places=0,
                default=0,
                help_text="개별 배송원의 2회차 용차 지급단가 override 값",
                max_digits=12,
                verbose_name="2회차 개인 용차 지급단가(가구당)",
            ),
        ),
        migrations.AddField(
            model_name="crewmember",
            name="personal_round_3_yongcha_pay_price",
            field=models.DecimalField(
                decimal_places=0,
                default=0,
                help_text="개별 배송원의 3회차 용차 지급단가 override 값",
                max_digits=12,
                verbose_name="3회차 개인 용차 지급단가(가구당)",
            ),
        ),
    ]
