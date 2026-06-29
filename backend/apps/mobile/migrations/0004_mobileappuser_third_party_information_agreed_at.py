from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mobile", "0003_mobileappuser_signup_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="mobileappuser",
            name="third_party_information_agreed_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="제3자 정보제공 동의 시각",
            ),
        ),
    ]
