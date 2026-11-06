from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def fixture_html(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def fixture_map() -> dict[str, str]:
    """Offline site graph used by cite-or-abstain tests."""
    return {
        "https://fixture.local/": fixture_html("home_with_pricing_link.html"),
        "https://fixture.local": fixture_html("home_with_pricing_link.html"),
        "https://fixture.local/pricing": fixture_html("pricing_pro.html"),
        "https://fixture.local/about": fixture_html("pricing_no_price.html"),
    }


def make_fetch(pages: dict[str, str]):
    def _fetch(url: str) -> tuple[str, str]:
        if url not in pages:
            raise LookupError(f"no fixture for {url}")
        return url, pages[url]

    return _fetch
