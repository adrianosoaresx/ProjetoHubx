from django.db import migrations, models
import django.utils.timezone
import django_extensions.db.fields


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0003_alter_dashboardconfig_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="dashboardfilter",
            name="created",
            field=django_extensions.db.fields.CreationDateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
                verbose_name="created",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="dashboardfilter",
            name="modified",
            field=django_extensions.db.fields.ModificationDateTimeField(
                auto_now=True,
                verbose_name="modified",
            ),
        ),
        migrations.AddField(
            model_name="dashboardfilter",
            name="deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="dashboardfilter",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="dashboardconfig",
            name="deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="dashboardconfig",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
