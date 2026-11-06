import httpx, re
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, unquote

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
q = "Stripe Pro plan monthly price"

# DDG instant answer
r = httpx.get("https://api.duckduckgo.com/", params={"q": q, "format": "json", "no_redirect": 1, "no_html": 1}, headers=headers, timeout=30)
print("DDG API", r.status_code, r.text[:400])

# Bing
url = f"https://www.bing.com/search?q={quote_plus(q)}"
r = httpx.get(url, headers=headers, follow_redirects=True, timeout=30)
print("Bing", r.status_code, len(r.text))
soup = BeautifulSoup(r.text, "lxml")
links = []
for a in soup.select("li.b_algo h2 a"):
    links.append(a.get("href"))
print("bing links", links[:8])
if not links:
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http") and "bing.com" not in href and "microsoft.com" not in href:
            links.append(href)
    print("fallback", links[:8])
