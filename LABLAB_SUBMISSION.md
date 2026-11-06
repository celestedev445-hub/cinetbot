# CiteBot — AMD AI League Match 4 (LabLab fields)

## Project title
CiteBot — Exact Web Answer Agent

## Short description
Asks a precise question, navigates public pages, and returns only an exact string found on a page with its source URL, or abstains when there is no proof.

## Long description
CiteBot is built for AMD AI League Match 4 (Intelligent Web Information Retrieval).

You ask a natural-language question, optionally with a start URL. CiteBot fetches pages, follows a few useful links, and extracts candidate answers. It only returns a value when that exact string appears on a fetched page, together with the source URL. If nothing is proven, it abstains with a clear reason (empty question, no search results, or no proof on pages).

Default path is rule-based (no LLM required). An optional LLM can re-rank candidates that are already proven on the page; it cannot invent new answers.

Interfaces: HTTP `POST /api/ask` and a small web UI. Offline fixtures and tests cover cite-or-abstain without network.

Stack: Python, FastAPI, httpx, BeautifulSoup4.

## Technology tags
Python, FastAPI, web agent, information retrieval, cite-or-abstain

## Public GitHub
https://github.com/celestedev445-hub/cinetbot

## Demo URL
Local: http://127.0.0.1:8080 after `uvicorn app.main:app --port 8080`
(Hosted demo URL: add once deployed)

## Team page
https://lablab.build/ai-hackathons/amd-lablab-ai-academy-challenge/florentdev
