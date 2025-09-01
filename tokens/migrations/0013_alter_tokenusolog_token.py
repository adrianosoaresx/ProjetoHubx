from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tokens", "0012_merge_20250821_1829"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tokenusolog",
            name="token",
            field=models.ForeignKey(
                to="tokens.tokenacesso",
                on_delete=models.CASCADE,
                related_name="logs",
                null=True,
                blank=True,
            ),
        ),
    ]
