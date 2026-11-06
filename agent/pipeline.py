from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlparse
import re

import httpx
from bs4 import BeautifulSoup

from .config import settings
from . import llm as llm_assist

FetchFn = Callable[[str], tuple[str, str]]


@dataclass
class AskResult:
    answer: str | None
    source_url: str | None
    hops: list[str] = field(default_factory=list)
    abstained: bool = False
    reason: str | None = None


PRICE_RE = re.compile(
    r"""(?ix)
    (?:
      (?:USD|EUR|GBP|XAF|FCFA|CFA)\s?[\$€£]?\s?\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?
      |
      [\$€£]\s?\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?(?:\s*/\s*(?:month|mois|mo|year|yr|an))?
      |
      \d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?\s*(?:USD|EUR|GBP|XAF|FCFA|CFA)(?:\s*/\s*(?:month|mois|mo|year|yr|an))?
    )
    """
)

CURRENCY_HINTS = ("$", "€", "£", "usd", "eur", "gbp", "fcfa", "xaf", "cfa", "/mo", "/month", "/mois")

STOP = {
    "what", "whats", "which", "where", "when", "how", "much", "many", "is", "the", "a", "an",
    "of", "for", "on", "in", "to", "and", "or", "plan", "plans", "price", "pricing", "monthly",
    "yearly", "annual", "cost", "costs", "quel", "quelle", "combien", "prix", "tarif", "mois",
    "an", "usd", "eur", "dollar", "euros", "website", "site", "page", "official",
    "pro", "starter", "basic", "premium", "plus", "enterprise", "business", "free", "standard",
    "team", "personal", "individual", "subscription", "abo", "offer", "offre",
}

PATHS = ("/pricing", "/plans", "/price", "/tarifs", "/pricing/", "/plans/", "/")


def _fetch(url: str) -> tuple[str, str]:
    """Fetch a remote page, or a local file via file:// URL."""
    parsed = urlparse(url)
    if parsed.scheme == "file":
        path = Path(parsed.path)
        # Windows file:///C:/... leaves an empty host and path like /C:/...
        if path.as_posix().startswith("/") and len(path.parts) > 1 and path.parts[0] == "/" and ":" in path.parts[1]:
            path = Path(path.as_posix().lstrip("/"))
        text = path.read_text(encoding="utf-8")
        return url, text

    headers = {"User-Agent": settings.user_agent}
    with httpx.Client(follow_redirects=True, timeout=settings.request_timeout_s) as client:
        r = client.get(url, headers=headers)
        r.raise_for_status()
        return str(r.url), r.text


def _visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return " ".join(soup.get_text(" ", strip=True).split())


def _brand_tokens(question: str) -> list[str]:
    caps = re.findall(r"\b([A-Z][a-zA-Z0-9]+)\b", question)
    words = re.findall(r"[A-Za-zÀ-ÿ0-9]+", question)
    out: list[str] = []
    for w in caps + words:
        low = w.lower()
        if low in STOP or len(low) < 3:
            continue
        if w not in out and low not in {x.lower() for x in out}:
            out.append(w)
    return out[:4]


def _search_seed_urls(question: str, limit: int = 8) -> list[str]:
    """Infer likely official pages from the brand name in the question.
    Public search engines often block datacenter IPs; this keeps CiteBot usable without a search API.
    """
    brands = _brand_tokens(question)
    seeds: list[str] = []
    for brand in brands:
        slug = re.sub(r"[^a-z0-9]", "", brand.lower())
        if len(slug) < 3:
            continue
        hosts = [
            f"https://www.{slug}.com",
            f"https://{slug}.com",
            f"https://www.{slug}.io",
            f"https://{slug}.io",
        ]
        for host in hosts:
            for path in PATHS:
                seeds.append(host.rstrip("/") + path)
    seen: set[str] = set()
    out: list[str] = []
    for u in seeds:
        if u not in seen:
            seen.add(u)
            out.append(u)
        if len(out) >= limit:
            break
    return out


def _candidate_links(base_url: str, html: str, question: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    q = question.lower()
    keywords = [w for w in q.replace("?", " ").split() if len(w) > 3 and w.lower() not in STOP]
    scored: list[tuple[int, str]] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
            continue
        abs_url = urljoin(base_url, href)
        if urlparse(abs_url).scheme not in ("http", "https", "file"):
            continue
        label = (a.get_text(" ", strip=True) + " " + href).lower()
        score = sum(1 for k in keywords if k in label)
        for hint in ("price", "pricing", "plan", "contact", "about", "faq", "tarif", "offre"):
            if hint in label:
                score += 2
        if score:
            scored.append((score, abs_url))
    scored.sort(key=lambda x: -x[0])
    seen: set[str] = set()
    out: list[str] = []
    for _, u in scored:
        if u not in seen:
            seen.add(u)
            out.append(u)
        if len(out) >= 3:
            break
    return out


def _is_plausible_price(token: str) -> bool:
    t = token.strip()
    if not t:
        return False
    if re.fullmatch(r"\d{1,3}", t):
        return False
    low = t.lower()
    if any(h in low for h in CURRENCY_HINTS):
        return True
    return bool(re.search(r"[\$€£]|USD|EUR|GBP|FCFA|XAF|CFA|/\s*(mo|month|mois)", t, re.I))


def _extract_candidates(question: str, text: str) -> list[tuple[int, str]]:
    if not text:
        return []
    q_words = [w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ0-9]+", question) if len(w) > 2]
    plan_words = [
        w
        for w in q_words
        if w in {"pro", "starter", "basic", "premium", "plus", "enterprise", "business", "free"}
    ]

    candidates: list[tuple[int, str]] = []
    for m in PRICE_RE.finditer(text):
        token = " ".join(m.group(0).split())
        if not _is_plausible_price(token):
            continue
        start, end = m.span()
        # Prefer plan name shortly *before* the price (avoids next plan heading leaking in)
        left = text[max(0, start - 80) : start].lower()
        window = text[max(0, start - 100) : end + 40].lower()
        score = 0
        for w in q_words:
            if w in window:
                score += 1
        for w in plan_words:
            # Strong boost when the asked plan appears just before this price
            if re.search(rf"\b{re.escape(w)}\b", left):
                score += 12
            elif re.search(rf"\b{re.escape(w)}\b", window):
                score += 2
            # Penalize if a *different* plan name is closer before the price
        other_plans = {"pro", "starter", "basic", "premium", "plus", "enterprise", "business", "free"} - set(plan_words)
        for w in other_plans:
            if re.search(rf"\b{re.escape(w)}\b", left[-50:]):
                score -= 10
        for hint in ("pricing", "plan", "month", "mois", "/mo"):
            if hint in window:
                score += 1
        if any(c in token for c in "$€£") or re.search(r"USD|EUR|FCFA", token, re.I):
            score += 2
        if re.search(r"/\s*(month|mois|mo)", token, re.I):
            score += 2
        # Slight preference for longer/more specific tokens
        score += min(len(token), 12) // 6
        candidates.append((score, token))
    candidates.sort(key=lambda x: (-x[0], -len(x[1])))
    return candidates


def _proven_on_page(token: str, text: str) -> bool:
    """Cite-or-abstain gate: the answer string must appear on the page."""
    if not token or not text:
        return False
    if token.lower() in text.lower():
        return True
    compact_t = token.replace(" ", "").lower()
    compact_page = text.replace(" ", "").lower()
    return compact_t in compact_page


def extract_answer(question: str, text: str) -> str | None:
    """Public helper used by tests: best cited price-like answer or None."""
    candidates = _extract_candidates(question, text)
    if not candidates:
        return None
    best_score, best = candidates[0]
    plan_words = {
        w.lower()
        for w in re.findall(r"[A-Za-zÀ-ÿ0-9]+", question)
        if w.lower() in {"pro", "starter", "basic", "premium", "plus", "enterprise", "business", "free"}
    }
    if best_score < 2 and not plan_words:
        return None
    if not _proven_on_page(best, text):
        return None

    # Optional LLM may only re-rank among proven candidates
    proven = [t for s, t in candidates if s >= 2 or plan_words]
    if not proven:
        proven = [best]
    suggested = llm_assist.suggest_answer(question, text, proven)
    if suggested and _proven_on_page(suggested, text):
        return suggested
    return best


def ask(
    question: str,
    start_url: str | None = None,
    *,
    fetch_fn: FetchFn | None = None,
) -> AskResult:
    """Navigate from start_url (or brand seed URLs) and return a cited answer or abstain.

    fetch_fn: optional (url) -> (final_url, html) for offline / fixture tests.
    """
    if not question or not question.strip():
        return AskResult(answer=None, source_url=None, abstained=True, reason="empty_question")

    fetch = fetch_fn or _fetch
    hops: list[str] = []
    queue: list[str] = []
    if start_url:
        queue.append(start_url.strip())
    else:
        seeds = _search_seed_urls(question)
        if not seeds:
            return AskResult(answer=None, source_url=None, abstained=True, reason="no_search_results")
        queue.extend(seeds)

    visited: set[str] = set()

    while queue and len(hops) < settings.max_hops:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        try:
            final_url, html = fetch(url)
        except Exception:
            continue
        hops.append(final_url)
        text = _visible_text(html)
        found = extract_answer(question, text)
        if found and _proven_on_page(found, text):
            return AskResult(answer=found, source_url=final_url, hops=hops, abstained=False)
        for link in _candidate_links(final_url, html, question):
            if link not in visited:
                queue.append(link)

    return AskResult(
        answer=None,
        source_url=None,
        hops=hops,
        abstained=True,
        reason="no_proof_on_pages",
    )
