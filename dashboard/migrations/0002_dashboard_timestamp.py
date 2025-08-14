from django.db import migrations


def create_initial_achievements(apps, schema_editor):
    Achievement = apps.get_model("dashboard", "Achievement")
    Achievement.objects.get_or_create(code="5_dashboards", defaults={"titulo": "", "descricao": "", "criterio": ""})
    Achievement.objects.get_or_create(code="100_inscricoes", defaults={"titulo": "", "descricao": "", "criterio": ""})

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
            model_name="achievement",
            old_name="created",
            new_name="created_at",
        ),
        migrations.RenameField(
            model_name="achievement",
            old_name="modified",
            new_name="updated_at",
        ),
        migrations.RenameField(
            model_name="userachievement",
            old_name="created",
            new_name="created_at",
        ),
        migrations.RenameField(
            model_name="userachievement",
            old_name="modified",
            new_name="updated_at",
        ),
        migrations.RemoveField(
            model_name="userachievement",
            name="completado_em",
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
        migrations.RunPython(create_initial_achievements, migrations.RunPython.noop),
    ]
