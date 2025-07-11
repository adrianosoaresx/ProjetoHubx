from datetime import date
from django.test import TestCase
from django.urls import reverse


class CalendarViewTests(TestCase):
    def test_month_navigation_context(self):
        url = reverse("agenda:calendario_mes", args=[2025, 5])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["data_atual"], date(2025, 5, 1))
        self.assertIn("prev_ano", resp.context)
        self.assertIn("next_ano", resp.context)

