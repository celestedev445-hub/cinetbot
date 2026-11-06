import httpx, re, json
from urllib.parse import quote

headers = {"User-Agent": "CiteBot/0.1 (AMD AI League)"}
q = "Stripe Pro plan monthly price"

# Wikipedia opensearch
r = httpx.get("https://en.wikipedia.org/w/api.php", params={"action":"opensearch","search":"Stripe","limit":5,"namespace":0,"format":"json"}, headers=headers, timeout=30)
print("wiki", r.status_code, r.text[:500])

# Wikidata search
r = httpx.get("https://www.wikidata.org/w/api.php", params={"action":"wbsearchentities","search":"Stripe","language":"en","format":"json","limit":5}, headers=headers, timeout=30)
print("wd search", r.status_code, r.text[:600])
data = r.json()
if data.get("search"):
    qid = data["search"][0]["id"]
    r2 = httpx.get("https://www.wikidata.org/wiki/Special:EntityData/" + qid + ".json", headers=headers, timeout=30)
    ent = r2.json()["entities"][qid]
    claims = ent.get("claims", {})
    sites = []
    for c in claims.get("P856", []):
        sites.append(c["mainsnak"]["datavalue"]["value"])
    print("official", sites)
