"""Test suite initialization for Django."""
import os
import sys
import django
from pathlib import Path
from django.test.utils import setup_test_environment, setup_databases

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "pytest" not in sys.modules:
    django.setup()
    setup_test_environment()
    setup_databases(verbosity=0, interactive=False)
