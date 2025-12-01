import pytest
from bs4 import BeautifulSoup
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory

from accounts.factories import UserFactory


@pytest.mark.django_db
class TestHeroProfileTemplate:
    def render_template(
        self,
        *,
        average,
        display,
        total=0,
        is_owner=False,
    ) -> str:
        profile = UserFactory()
        request = RequestFactory().get("/")
        request.user = AnonymousUser()

        context = {
            "profile": profile,
            "is_owner": is_owner,
            "hero_title": profile.display_name,
            "hero_subtitle": "",
            "perfil_avaliacao_media": average,
            "perfil_avaliacao_display": display,
            "perfil_avaliacao_total": total,
            "perfil_avaliar_url": "/avaliar/",
            "perfil_avaliar_identifier": str(profile.public_id),
            "perfil_feedback_exists": False,
            "request": request,
        }

        return render_to_string("_components/hero_profile.html", context)

    def parse(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    def test_renders_full_stars_when_average_is_maximum(self):
        html = self.render_template(average=5, display="5,0", total=3)
        soup = self.parse(html)
        stars = soup.select("[data-rating-state]")

        assert len(stars) == 5
        assert sum(1 for star in stars if star["data-rating-state"] == "full") == 5
        assert all(star["data-rating-state"] != "half" for star in stars)
        assert all(star["data-rating-state"] != "empty" for star in stars)

        empty_label = soup.select_one("[data-user-rating-empty]")
        assert empty_label is not None
        assert "hidden" in (empty_label.get("class") or [])
        assert "5,0" in html

    def test_renders_empty_stars_when_average_is_missing(self):
        html = self.render_template(average=None, display="", total=0)
        soup = self.parse(html)
        stars = soup.select("[data-rating-state]")

        assert len(stars) == 5
        assert sum(1 for star in stars if star["data-rating-state"] == "empty") == 5
        assert all(star["data-rating-state"] != "full" for star in stars)

        empty_label = soup.select_one("[data-user-rating-empty]")
        assert empty_label is not None
        assert "Sem avaliações" in empty_label.text
        assert "hidden" not in (empty_label.get("class") or [])
