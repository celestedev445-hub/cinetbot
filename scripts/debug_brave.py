import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
q = quote_plus("Stripe Pro plan monthly price")
r = httpx.get(f"https://search.brave.com/search?q={q}", headers=headers, follow_redirects=True, timeout=30)
print(r.status_code, len(r.text), r.url)
soup = BeautifulSoup(r.text, "lxml")
for a in soup.select("a[href]")[:30]:
    href = a.get("href","")
    if href.startswith("http") and "brave.com" not in href:
        print(href[:160], "|", a.get_text(" ", strip=True)[:60])
