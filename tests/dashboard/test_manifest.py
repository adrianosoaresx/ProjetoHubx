import json
from pathlib import Path


def test_manifest_fields():
    data = json.loads(Path("static/manifest.json").read_text())
    assert data["name"] == "Hubx Dashboard"
    assert data["short_name"] == "Dashboard"
    assert data["start_url"] == "/dashboard/"
    assert data["display"] == "standalone"
    assert data["background_color"] == "#ffffff"
    assert data["theme_color"] == "#0f172a"
    sizes = {icon["sizes"] for icon in data["icons"]}
    assert {"192x192", "512x512"} <= sizes
