# CiteBot — Exact Web Answer Agent

**AMD AI League — Match 4: Intelligent Web Information Retrieval**  
Team: **[florentdev](https://lablab.build/ai-hackathons/amd-lablab-ai-academy-challenge/florentdev)**

CiteBot answers a precise natural-language question by navigating the web (or a page you point it at), then returns the **exact value found on the page with a source URL** — or **abstains** if there is no proof.

> **Product positioning:** worldwide usable Exact Web Answer Agent.  
> African shopkeepers / Boutiko stories are **demo narrative only** — not a product constraint.  
> This repo must **never** touch Boutiko / Meta WhatsApp config.

## Why cite-or-abstain

Hallucinated prices and facts are worse than silence. CiteBot only returns an answer when the string appears on a fetched page. Otherwise it abstains with a reason (`empty_question`, `no_search_results`, `no_proof_on_pages`).

## Interfaces

- **Primary:** HTTP API `POST /api/ask` + small web UI
- **Optional later:** WhatsApp on a **separate** number / WABA — **do not touch Boutiko Meta config**

## Stack

- Python 3.11+, FastAPI, httpx, BeautifulSoup4, pydantic-settings
- Rule-based extraction by default
- Optional LLM assist via env (`USE_LLM=true` + `OPENAI_API_KEY`) — LLM may only **re-rank** candidates already proven on the page

## Quick start

```bash
cd citebot   # or C:\dev\citebot on Windows
python -m venv .venv

# Windows
.\.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # optional

uvicorn app.main:app --reload --port 8080
```

Open http://127.0.0.1:8080

Windows helper: `scripts\run_dev.ps1`  
Linux/macOS helper: `scripts/run_dev.sh`

## API

```http
POST /api/ask
Content-Type: application/json

{
  "question": "What is the Pro plan price?",
  "start_url": "https://example.com/pricing"
}
```

`start_url` is **optional** but recommended: point CiteBot at any public page (pricing, FAQ, docs). Without it, CiteBot guesses official hostnames from brand tokens in the question.

Success:

```json
{
  "answer": "$29 / month",
  "source_url": "https://example.com/pricing",
  "hops": ["https://example.com/pricing"],
  "abstained": false,
  "reason": null
}
```

Abstain:

```json
{
  "answer": null,
  "source_url": null,
  "hops": ["https://example.com/about"],
  "abstained": true,
  "reason": "no_proof_on_pages"
}
```

Health: `GET /health`

## Offline fixtures & tests

```bash
pytest -q
```

Fixtures live in `tests/fixtures/` (pricing with Pro price, about page without price, home with pricing link). Tests run **without network** via an injectable `fetch_fn`.

## Project layout

```
agent/          fetch, link pick, extract, cite-or-abstain, optional LLM
app/            FastAPI + static UI
tests/          unit + API tests + HTML fixtures
scripts/        local helpers
```

## Environment

See `.env.example`:

| Variable | Default | Meaning |
|----------|---------|---------|
| `MAX_HOPS` | `5` | Max pages to visit per question |
| `REQUEST_TIMEOUT_S` | `20` | HTTP timeout |
| `USE_LLM` | `false` | Enable optional LLM re-rank |
| `OPENAI_API_KEY` | empty | Required only if `USE_LLM=true` |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat model |
| `OPENAI_BASE_URL` | OpenAI | Compatible gateway URL |

## Boutiko / Meta

**Do not change** Boutiko webhook, tokens, or WhatsApp number. CiteBot stays a separate codebase and deploy.
