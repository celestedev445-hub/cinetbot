from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

from agent import ask

ROOT = Path(__file__).resolve().parent
app = FastAPI(
    title="CiteBot — Exact Web Answer Agent",
    version="0.2.0",
    description="Answers factual web questions with a cited source URL, or abstains.",
)
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")


class AskRequest(BaseModel):
    question: str
    start_url: str | None = None

    @field_validator("start_url", mode="before")
    @classmethod
    def empty_url_to_none(cls, v):  # noqa: ANN001
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("start_url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is None:
            return None
        lower = v.lower()
        if lower.startswith(("http://", "https://", "file://")):
            return v
        if "://" not in v:
            return "https://" + v.lstrip("/")
        raise ValueError("start_url must be http(s) or file://")


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return (ROOT / "templates" / "index.html").read_text(encoding="utf-8")


@app.post("/api/ask")
def api_ask(body: AskRequest) -> dict:
    result = ask(body.question, body.start_url)
    return {
        "answer": result.answer,
        "source_url": result.source_url,
        "hops": result.hops,
        "abstained": result.abstained,
        "reason": result.reason,
    }


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "citebot", "version": "0.2.0"}
