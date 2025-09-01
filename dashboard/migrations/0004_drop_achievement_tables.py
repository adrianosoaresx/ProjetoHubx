from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0003_dashboardcustommetric"),
    ]

    operations = [
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS dashboard_userachievement;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS dashboard_achievement;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
