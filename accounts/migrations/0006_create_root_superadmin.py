from django.db import migrations
from django.contrib.auth.hashers import make_password


def create_root_user(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    if not User.objects.filter(username='root').exists():
        User.objects.create(
            username='root',
            first_name='root',
            tipo='superadmin',
            is_superuser=True,
            is_staff=True,
            password=make_password('J0529*4351'),
        )

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_user_organizacao_user_tipo'),
    ]

    operations = [
        migrations.RunPython(create_root_user),
    ]
