"""Test suite initialization for Django."""

import os
import sys
from pathlib import Path

import django
from django.test.utils import setup_databases, setup_test_environment

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hubx.settings")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "pytest" not in sys.modules:
    django.setup()
    setup_test_environment()
    setup_databases(verbosity=0, interactive=False)
