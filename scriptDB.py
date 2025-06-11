"""Ensure that all required database tables exist."""
import os
import django
from django.core.management import call_command
from django.db import connection

REQUIRED_TABLES = [
    'auth_user',
    'auth_group',
    'auth_permission',
    'django_content_type',
    'django_migrations',
    'django_session',
    'empresas_empresa',
    'empresas_tag',
    'empresas_empresa_tags',
    'perfil_perfil',
    'perfil_notificationsettings',
]


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Hubx.settings')
    django.setup()

    existing = connection.introspection.table_names()
    missing = [t for t in REQUIRED_TABLES if t not in existing]

    if missing:
        print('Creating missing tables:', ', '.join(missing))
        call_command('migrate', interactive=False)
    else:
        print('All required tables are present.')


if __name__ == '__main__':
    main()
