from pathlib import Path

from agent.pipeline import ask, extract_answer, _visible_text
from tests.conftest import fixture_html, fixture_map, make_fetch

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_empty_question_abstains():
    r = ask("")
    assert r.abstained
    assert r.reason == "empty_question"


def test_extract_pro_price_from_fixture():
    html = fixture_html("pricing_pro.html")
    text = _visible_text(html)
    ans = extract_answer("What is the Pro plan monthly price?", text)
    assert ans is not None
    assert "29" in ans
    assert "$" in ans or "USD" in ans.upper() or "/ month" in ans or "/month" in ans.replace(" ", "")


def test_extract_abstains_when_no_price():
    html = fixture_html("pricing_no_price.html")
    text = _visible_text(html)
    ans = extract_answer("What is the Pro plan monthly price?", text)
    assert ans is None


def test_ask_with_start_url_offline_cites():
    pages = fixture_map()
    r = ask(
        "What is the Pro plan monthly price?",
        start_url="https://fixture.local/pricing",
        fetch_fn=make_fetch(pages),
    )
    assert not r.abstained
    assert r.answer is not None
    assert "29" in r.answer
    assert r.source_url == "https://fixture.local/pricing"
    assert "https://fixture.local/pricing" in r.hops


def test_ask_follows_pricing_link_then_cites():
    pages = fixture_map()
    r = ask(
        "What is the Acme Pro plan price?",
        start_url="https://fixture.local/",
        fetch_fn=make_fetch(pages),
    )
    assert not r.abstained
    assert r.answer is not None
    assert "29" in r.answer
    assert r.source_url == "https://fixture.local/pricing"
    assert len(r.hops) >= 2


def test_ask_abstains_on_about_page():
    pages = fixture_map()
    r = ask(
        "What is the Pro plan monthly price?",
        start_url="https://fixture.local/about",
        fetch_fn=make_fetch(pages),
    )
    # About has a pricing link — agent may hop. Force single-hop by using a map
    # without follow-up, or assert: if it only has about, abstain.
    pages_only = {"https://fixture.local/about": fixture_html("pricing_no_price.html")}
    # rewrite about fixture without external pricing that resolves:
    html = fixture_html("pricing_no_price.html").replace(
        '<a href="/pricing">See pricing</a>',
        "<p>No pricing listed.</p>",
    )
    pages_only = {"https://fixture.local/about": html}
    r = ask(
        "What is the Pro plan monthly price?",
        start_url="https://fixture.local/about",
        fetch_fn=make_fetch(pages_only),
    )
    assert r.abstained
    assert r.reason == "no_proof_on_pages"
    assert r.answer is None


def test_cite_or_abstain_requires_proof_on_page():
    """Answer token must appear in page text — never invent."""
    text = "Our Pro plan is $29 / month. Starter is $9 / month."
    ans = extract_answer("Pro plan monthly price?", text)
    assert ans is not None
    assert ans.lower() in text.lower() or ans.replace(" ", "").lower() in text.replace(" ", "").lower()


def test_search_without_url_does_not_require_start_url():
    # May abstain if network blocked; must not crash with start_url_required
    r = ask("Stripe Pro plan monthly price")
    assert r.reason != "start_url_required_in_mvp"


def test_file_url_start(tmp_path: Path):
    src = FIXTURES / "pricing_pro.html"
    dest = tmp_path / "pricing_pro.html"
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    file_url = dest.resolve().as_uri()
    r = ask("What is the Pro plan monthly price?", start_url=file_url)
    assert not r.abstained
    assert r.answer is not None
    assert "29" in r.answer
