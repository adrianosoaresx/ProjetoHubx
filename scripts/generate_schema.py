"""Gera o SQL de criação das tabelas para uso manual."""
import io
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import django
from django.core.management import call_command


def main(out_file="schema.sql"):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")
    django.setup()

    apps_and_migrations = {
        "usuarios": "0001",
        "empresas": "0001",
        "perfil": "0002",
    }
    with open(out_file, "w") as f:
        for app, mig in apps_and_migrations.items():
            buf = io.StringIO()
            call_command("sqlmigrate", app, mig, stdout=buf)
            f.write(buf.getvalue())
            f.write("\n")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "schema.sql"
    main(out)
