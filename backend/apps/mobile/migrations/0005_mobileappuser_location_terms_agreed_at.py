from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mobile", "0004_mobileappuser_third_party_information_agreed_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="mobileappuser",
            name="location_terms_agreed_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="위치정보기반 서비스 이용약관 동의 시각",
            ),
        ),
    ]
