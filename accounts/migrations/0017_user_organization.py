from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0016_delete_tokenacesso'),
        ('organizacoes', '0002_organizacao_created_at_organizacao_updated_at'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='organizacao',
            new_name='organization',
        ),
        migrations.AlterField(
            model_name='user',
            name='organization',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='users',
                to='organizacoes.organizacao',
                null=True,
                blank=True,
            ),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(
                fields=['username', 'organization'],
                name='accounts_user_username_org_uniq',
            ),
        ),
    ]
