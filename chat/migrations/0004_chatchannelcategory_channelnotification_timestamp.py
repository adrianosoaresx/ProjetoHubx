from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0003_chatparticipant_chatfavorite_timestamp_softdelete"),
    ]

    operations = [
        migrations.RenameField(
            model_name="chatchannel",
            old_name="created",
            new_name="created_at",
        ),
        migrations.RenameField(
            model_name="chatchannel",
            old_name="modified",
            new_name="updated_at",
        ),
        migrations.AlterField(
            model_name="chatchannel",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AlterField(
            model_name="chatchannel",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.RenameField(
            model_name="chatchannelcategory",
            old_name="created",
            new_name="created_at",
        ),
        migrations.RenameField(
            model_name="chatchannelcategory",
            old_name="modified",
            new_name="updated_at",
        ),
        migrations.AlterField(
            model_name="chatchannelcategory",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AlterField(
            model_name="chatchannelcategory",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.RenameField(
            model_name="chatnotification",
            old_name="created",
            new_name="created_at",
        ),
        migrations.RenameField(
            model_name="chatnotification",
            old_name="modified",
            new_name="updated_at",
        ),
        migrations.AlterField(
            model_name="chatnotification",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AlterField(
            model_name="chatnotification",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="chatchannelcategory",
            name="deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="chatchannelcategory",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RenameIndex(
            model_name="chatfavorite",
            new_name="chat_chatfa_user_id_e60d2e_idx",
            old_name="chat_chatfa_user_id_7580ff_idx",
        ),
    ]

