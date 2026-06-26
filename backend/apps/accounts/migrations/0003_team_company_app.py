from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_team_yongcha_rates"),
    ]

    operations = [
        migrations.AddField(
            model_name="team",
            name="company_app",
            field=models.CharField(
                choices=[("cheonha", "CHEONHA"), ("abc", "ABC")],
                db_index=True,
                default="cheonha",
                max_length=20,
                verbose_name="회사 앱 코드",
            ),
        ),
        migrations.AlterField(
            model_name="team",
            name="code",
            field=models.CharField(max_length=10, verbose_name="조 코드"),
        ),
        migrations.AddConstraint(
            model_name="team",
            constraint=models.UniqueConstraint(
                fields=("company_app", "code"),
                name="accounts_team_company_app_code_uniq",
            ),
        ),
    ]
