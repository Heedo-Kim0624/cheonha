from django.db import migrations, models


def sync_round_yongcha_columns(apps, schema_editor):
    from django.db.models import F
    from apps.crew.models import CrewMember

    connection = schema_editor.connection
    table_name = CrewMember._meta.db_table
    existing_tables = set(connection.introspection.table_names())
    if table_name not in existing_tables:
        schema_editor.create_model(CrewMember)
    else:
        with connection.cursor() as cursor:
            columns = {
                column.name
                for column in connection.introspection.get_table_description(cursor, table_name)
            }
        for field_name in (
            'yongcha_pay_price',
            'round_1_is_yongcha',
            'round_2_is_yongcha',
            'round_3_is_yongcha',
        ):
            field = CrewMember._meta.get_field(field_name)
            if field.column in columns:
                continue
            schema_editor.add_field(CrewMember, field)
            columns.add(field.column)

    CrewMember.objects.filter(
        is_yongcha=True,
        yongcha_pay_price=0,
    ).update(yongcha_pay_price=F('pay_price'))


class Migration(migrations.Migration):

    dependencies = [
        ('crew', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(sync_round_yongcha_columns, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='crewmember',
                    name='round_1_is_yongcha',
                    field=models.BooleanField(default=False, verbose_name='1회차 용차'),
                ),
                migrations.AddField(
                    model_name='crewmember',
                    name='round_2_is_yongcha',
                    field=models.BooleanField(default=False, verbose_name='2회차 용차'),
                ),
                migrations.AddField(
                    model_name='crewmember',
                    name='round_3_is_yongcha',
                    field=models.BooleanField(default=False, verbose_name='3회차 용차'),
                ),
                migrations.AddField(
                    model_name='crewmember',
                    name='yongcha_pay_price',
                    field=models.DecimalField(decimal_places=0, default=0, help_text='원 단위 - 용차 기사에게 지급하는 가구당 금액', max_digits=12, verbose_name='용차 지급단가(가구당)'),
                ),
            ],
        ),
    ]
