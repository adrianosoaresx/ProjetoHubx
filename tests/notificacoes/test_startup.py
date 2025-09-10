import os
import subprocess
import sys


def test_django_setup_without_db_warning() -> None:
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "Hubx.settings"

    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import warnings, django; warnings.simplefilter('always'); django.setup()",
        ],
        env=env,
        capture_output=True,
        text=True,
    )

    assert "Accessing the database during app initialization is discouraged" not in proc.stderr, proc.stderr
    assert proc.returncode == 0
