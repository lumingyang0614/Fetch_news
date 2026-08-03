from pathlib import Path


def test_retention_setting_is_documented() -> None:
    example = Path(".env.example").read_text(encoding="utf-8")
    assert "MAX_NEWS_PER_STOCK=20" in example
