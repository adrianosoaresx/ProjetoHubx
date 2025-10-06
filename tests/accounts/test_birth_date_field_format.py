from datetime import date

from accounts.forms import InformacoesPessoaisForm
from accounts.models import User


def test_birth_date_field_renders_iso_format():
    user = User(email="user@example.com", username="user")
    user.birth_date = date(1990, 1, 1)

    form = InformacoesPessoaisForm(instance=user)

    rendered = str(form["birth_date"])

    assert "value=\"1990-01-01\"" in rendered
