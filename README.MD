# RiskSignal API

RiskSignal API is a small REST service that turns batches of news headlines into a single, actionable risk signal. It is made for people who care about risk but don’t have time to read every article: analysts, PMs, founders, and risk/compliance teams.

Given a list of recent headlines, the API returns a normalized 0–100 risk score, a low/medium/high level, dominant risk tags, and a per‑headline breakdown so you can see what actually drives the risk.

---

## Why RiskSignal?

Most teams that care about risk are drowning in news feeds and alerts. There is always another stream of headlines, but never enough time or attention to read them all.

RiskSignal API gives you a single, opinionated signal per batch of news, plus a few risk tags that tell you where the pressure comes from (sanctions, regulation, geopolitics, banking, etc.). You can plug it into your dashboards, alerting systems or internal tools.

Use it when you want to know:

- Is the risk environment around this topic low, medium or high?
- Which themes dominate today’s headlines: sanctions, regulation, war, banking stress?
- Which specific headlines are actually moving the risk score?

---

## Features

- Single `overall_risk_score` (0–100) per batch of news.
- Simple `risk_level` (`low`, `medium`, `high`) with clear thresholds.
- `top_risk_tags` such as `sanctions_risk`, `geopolitics_risk`, `banking_risk`.
- Per‑headline sentiment, categories, `affects_score` and numeric `risk_contribution`.
- Transparent heuristic v1 (keywords + category weights), easy to tweak or replace with ML/LLM.
- FastAPI + Pydantic + Uvicorn, one main endpoint: `POST /risk-signal`.
- Interactive docs at `/docs`.

---

## Tech Stack

- Python 3.10+
- FastAPI
- Pydantic
- Uvicorn

## Run with Docker

Build and run the container:

```bash
docker build -t risk-signal-api .
docker run -p 8000:8000 risk-signal-api

Or using docker compose:

docker compose up --build
Then open:

http://127.0.0.1:8000/health

http://127.0.0.1:8000/docs