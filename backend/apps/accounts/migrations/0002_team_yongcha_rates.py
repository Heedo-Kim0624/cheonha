from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="team",
            name="yongcha_pay_price",
            field=models.DecimalField(
                decimal_places=0,
                default=3000,
                help_text="원 단위 - 전체 용차 기사에게 지급하는 가구당 금액",
                max_digits=12,
                verbose_name="용차 지급단가(가구당)",
            ),
        ),
        migrations.AddField(
            model_name="team",
            name="round_1_yongcha_pay_price",
            field=models.DecimalField(
                decimal_places=0,
                default=3000,
                help_text="원 단위 - 정규 기사 중 1회차만 용차인 경우 지급하는 가구당 금액",
                max_digits=12,
                verbose_name="1회차 용차 지급단가(가구당)",
            ),
        ),
        migrations.AddField(
            model_name="team",
            name="round_2_yongcha_pay_price",
            field=models.DecimalField(
                decimal_places=0,
                default=3000,
                help_text="원 단위 - 정규 기사 중 2회차만 용차인 경우 지급하는 가구당 금액",
                max_digits=12,
                verbose_name="2회차 용차 지급단가(가구당)",
            ),
        ),
        migrations.AddField(
            model_name="team",
            name="round_3_yongcha_pay_price",
            field=models.DecimalField(
                decimal_places=0,
                default=3000,
                help_text="원 단위 - 정규 기사 중 3회차만 용차인 경우 지급하는 가구당 금액",
                max_digits=12,
                verbose_name="3회차 용차 지급단가(가구당)",
            ),
        ),
    ]
