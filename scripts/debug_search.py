import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, parse_qs, urlparse

q = quote_plus("Stripe Pro plan monthly price USD")
url = f"https://html.duckduckgo.com/html/?q={q}"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
r = httpx.get(url, headers=headers, follow_redirects=True, timeout=30)
print("status", r.status_code, "final", r.url, "len", len(r.text))
print(r.text[:1200])
soup = BeautifulSoup(r.text, "lxml")
print("result__a", len(soup.select("a.result__a")))
for a in soup.find_all("a", href=True)[:25]:
    print(a.get("class"), (a.get("href") or "")[:140])
