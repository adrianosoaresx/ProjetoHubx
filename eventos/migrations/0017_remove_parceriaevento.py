from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("eventos", "0016_evento_briefing_evento_parcerias"),
    ]

    operations = [
        migrations.DeleteModel(
            name="ParceriaEvento",
        ),
    ]
