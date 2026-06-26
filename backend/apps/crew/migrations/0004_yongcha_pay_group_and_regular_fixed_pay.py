from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_company_app_management"),
        ("crew", "0003_personal_round_yongcha_pay_prices"),
    ]

    operations = [
        migrations.CreateModel(
            name="YongchaPayGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="생성일")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="수정일")),
                (
                    "company_app",
                    models.CharField(db_index=True, default="cheonha", max_length=40),
                ),
                ("name", models.CharField(max_length=100)),
                ("round_1_base_pay", models.DecimalField(decimal_places=0, default=0, max_digits=12)),
                ("round_1_base_households", models.PositiveIntegerField(default=0)),
                ("round_1_extra_household_pay", models.DecimalField(decimal_places=0, default=0, max_digits=12)),
                ("round_2_base_pay", models.DecimalField(decimal_places=0, default=0, max_digits=12)),
                ("round_2_base_households", models.PositiveIntegerField(default=0)),
                ("round_2_extra_household_pay", models.DecimalField(decimal_places=0, default=0, max_digits=12)),
                ("round_3_base_pay", models.DecimalField(decimal_places=0, default=0, max_digits=12)),
                ("round_3_base_households", models.PositiveIntegerField(default=0)),
                ("round_3_extra_household_pay", models.DecimalField(decimal_places=0, default=0, max_digits=12)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="yongchapaygroup_created",
                        to="accounts.user",
                        verbose_name="생성자",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="yongchapaygroup_updated",
                        to="accounts.user",
                        verbose_name="수정자",
                    ),
                ),
            ],
            options={
                "db_table": "crew_yongcha_pay_group",
                "ordering": ["company_app", "name"],
            },
        ),
        migrations.AddField(
            model_name="crewmember",
            name="regular_round_1_base_pay",
            field=models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name="1회차 정규 고정급"),
        ),
        migrations.AddField(
            model_name="crewmember",
            name="regular_round_2_base_pay",
            field=models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name="2회차 정규 고정급"),
        ),
        migrations.AddField(
            model_name="crewmember",
            name="regular_round_3_base_pay",
            field=models.DecimalField(decimal_places=0, default=0, max_digits=12, verbose_name="3회차 정규 고정급"),
        ),
        migrations.AddField(
            model_name="crewmember",
            name="yongcha_pay_group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="crew_members",
                to="crew.yongchapaygroup",
                verbose_name="용차 팀단가",
            ),
        ),
        migrations.AddConstraint(
            model_name="yongchapaygroup",
            constraint=models.UniqueConstraint(
                fields=("company_app", "name"),
                name="crew_yongcha_pay_group_company_name_uniq",
            ),
        ),
    ]
