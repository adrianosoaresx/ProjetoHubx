from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="dashboardfilter",
            old_name="created",
            new_name="created_at",
        ),
        migrations.RenameField(
            model_name="dashboardfilter",
            old_name="modified",
            new_name="updated_at",
        ),
        migrations.RenameField(
            model_name="dashboardconfig",
            old_name="created",
            new_name="created_at",
        ),
        migrations.RenameField(
            model_name="dashboardconfig",
            old_name="modified",
            new_name="updated_at",
        ),
        migrations.RenameField(
            model_name="dashboardlayout",
            old_name="created",
            new_name="created_at",
        ),
        migrations.RenameField(
            model_name="dashboardlayout",
            old_name="modified",
            new_name="updated_at",
        ),
        migrations.AlterModelOptions(
            name="dashboardconfig",
            options={"get_latest_by": "updated_at"},
        ),
        migrations.AlterModelOptions(
            name="dashboardlayout",
            options={"get_latest_by": "updated_at"},
        ),
    ]
