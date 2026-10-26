import json
from pathlib import Path
import update


def test_weather_labels():
    assert update.weather_label(0) == "Clear sky"
    assert update.weather_label(95) == "Thunderstorm"
    assert update.weather_label(None) == "Conditions unavailable"


def test_dedupe_preserves_first_item():
    items = [{"url": "https://example.org/a", "title": "A"}, {"url": "https://example.org/a/", "title": "A duplicate"}, {"url": "https://example.org/b", "title": "B"}]
    result = update.dedupe(items)
    assert len(result) == 2
    assert result[0]["title"] == "A"


def test_brief_does_not_need_every_source():
    brief = update.build_brief([], [], None)
    assert brief and "dashboard" in brief[0].lower()


def test_config_has_weather_coordinates():
    cfg = json.loads((Path(__file__).parent / "config.json").read_text())
    assert -90 <= cfg["weather"]["latitude"] <= 90
    assert -180 <= cfg["weather"]["longitude"] <= 180
