from django.db import migrations


def copy_timestamps(apps, schema_editor):
    DashboardFilter = apps.get_model("dashboard", "DashboardFilter")
    for filtro in DashboardFilter.objects.all():
        filtro.created = filtro.created_at
        filtro.modified = filtro.updated_at
        filtro.save(update_fields=["created", "modified"])


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0004_add_timestamp_and_softdelete"),
    ]

    operations = [
        migrations.RunPython(copy_timestamps, reverse_code=migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="dashboardfilter",
            name="created_at",
        ),
        migrations.RemoveField(
            model_name="dashboardfilter",
            name="updated_at",
        ),
    ]
