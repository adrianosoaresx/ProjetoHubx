from django.db import migrations

def seed_admin_group_permissions(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    User = apps.get_model('accounts', 'User')

    # Garantir grupo "Admin"
    admin_group, _ = Group.objects.get_or_create(name='Admin')

    # ContentType de Evento
    try:
        ct = ContentType.objects.get(app_label='eventos', model='evento')
    except ContentType.DoesNotExist:
        return  # se ainda não existir, nada a fazer

    # Permissões padrão do modelo
    perms = Permission.objects.filter(content_type=ct, codename__in=[
        'add_evento', 'change_evento', 'delete_evento', 'view_evento'
    ])
    admin_group.permissions.add(*list(perms))

    # Vincular usuários ADMIN ao grupo Admin
    admin_users = User.objects.filter(user_type='admin')
    for u in admin_users:
        u.groups.add(admin_group)


def unseed_admin_group_permissions(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    try:
        admin_group = Group.objects.get(name='Admin')
    except Group.DoesNotExist:
        return
    # Não removemos o grupo automaticamente para evitar perda de configurações manuais


class Migration(migrations.Migration):
    dependencies = [
        ('eventos', '0008_alter_evento_numero_presentes'),
        ('accounts', '0001_initial'),
        ('auth', '__latest__'),
    ]

    operations = [
        migrations.RunPython(seed_admin_group_permissions, reverse_code=unseed_admin_group_permissions),
    ]
