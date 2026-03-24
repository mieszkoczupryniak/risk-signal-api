# RiskSignal API

RiskSignal API is a lightweight news-based risk signal service for macro, EM and sector analysts.  
It ingests batches of headlines and returns an overall risk score, granular risk tags and a simple trend view between two periods.

---

## Features

- **Batch risk scoring** – compute an overall 0–100 risk score from a set of news headlines.
- **Risk level bands** – map the score into low / medium / high bands for quick interpretation.
- **Granular risk tags** – generate specific tags such as `regulatory_risk_eu`, `sanctions_risk_russia`, `banking_stress_us`.
- **Trend analysis** – compare two periods (e.g. previous vs current week) and get direction, delta and main risk drivers.
- **FastAPI + Docker** – simple, portable microservice that can run locally or on platforms like Railway.

---

## API Overview

### 1. `POST /risk-signal`

Compute a risk signal for a single batch of news.

**Request body**
```json
{
  "items": [
    {
      "headline": "EU considers new sanctions on Russian oil exports",
      "body": "Officials are debating additional sanctions on selected Russian oil shipments.",
      "source": "Reuters",
      "published_at": "2026-03-22T10:00:00Z",
      "region": "EU",
      "topic_hint": "energy"
    },
    {
      "headline": "European banks face stress over energy sector exposure",
      "body": "Several EU banks flagged for increased risk due to concentrated energy lending.",
      "source": "FT",
      "published_at": "2026-03-22T09:00:00Z",
      "region": "EU",
      "topic_hint": "banking"
    }
  ],
  "focus": "energy",
  "horizon_days": 7
}
```

**Response body (example)**
```json
{
  "overall_risk_score": 38,
  "risk_level": "medium",
  "top_risk_tags": [
    "regulatory_risk_eu",
    "banking_stress_eu",
    "energy_supply_risk_eu"
  ],
  "summary": "Current headline set indicates a medium risk environment with dominant themes around regulatory_risk_eu, banking_stress_eu, energy_supply_risk_eu. Overall risk appears moderate and should be monitored based on recent news. Use this signal as a quick screening layer, not a full replacement for in-depth analysis.",
  "methodology_note": "This is a simple v1 heuristic based on keyword matching and category weights. Each negative headline increases the score depending on its category, while positive news can slightly offset risk. The overall score is normalized to a 0–100 range and mapped to low/medium/high bands. This is not a statistical or machine learning model and should be treated as an early signal only.",
  "items": [
    {
      "headline": "EU considers new sanctions on Russian oil exports",
      "sentiment": "negative",
      "categories": ["sanctions", "energy"],
      "affects_score": true,
      "risk_contribution": 7
    },
    {
      "headline": "European banks face stress over energy sector exposure",
      "sentiment": "negative",
      "categories": ["banking", "energy"],
      "affects_score": true,
      "risk_contribution": 5
    }
  ]
}
```

---

### 2. `POST /risk-signal/trend`

Compare risk between two periods (e.g. previous week vs current week) and return the trend.

**Request body**
```json
{
  "baseline": {
    "period_label": "previous_week",
    "items": [
      {
        "headline": "EU signals possible sanctions on Russian oil exports",
        "body": "EU officials are debating initial sanctions targeting selected Russian oil shipments.",
        "source": "Reuters",
        "published_at": "2026-03-15T10:00:00Z",
        "region": "EU",
        "topic_hint": "energy"
      }
    ]
  },
  "current": {
    "period_label": "current_week",
    "items": [
      {
        "headline": "EU approves new sanctions package on Russian oil exports",
        "body": "A stronger round of sanctions on Russian oil is approved, hitting shipping and insurance.",
        "source": "Reuters",
        "published_at": "2026-03-22T10:00:00Z",
        "region": "EU",
        "topic_hint": "energy"
      },
      {
        "headline": "European banks face stress over energy exposure",
        "body": "Several EU banks flagged for increased risk due to concentrated energy-sector lending.",
        "source": "FT",
        "published_at": "2026-03-22T09:00:00Z",
        "region": "EU",
        "topic_hint": "banking"
      }
    ]
  },
  "focus": "energy",
  "horizon_days": 7
}
```

**Response body (example)**
```json
{
  "baseline": {
    "period_label": "previous_week",
    "overall_risk_score": 7,
    "risk_level": "low"
  },
  "current": {
    "period_label": "current_week",
    "overall_risk_score": 13,
    "risk_level": "low"
  },
  "delta": {
    "score_change": 6,
    "direction": "up",
    "comment": "Risk moved up by 6 points, driven mainly by regulatory_risk_eu, banking_stress_eu."
  },
  "driver_tags": [
    "regulatory_risk_eu",
    "banking_stress_eu"
  ],
  "methodology_note": "Trend is computed by running the existing heuristic on both periods and comparing scores."
}
```

---

### 3. `GET /health`

Simple healthcheck endpoint used for container orchestration and uptime checks.

**Response body**
```json
{
  "status": "ok"
}
```

---

## How to Run Locally

### 1. Install dependencies
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run the API with Uvicorn
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Then open:

- Swagger UI: http://127.0.0.1:8000/docs
- Healthcheck: http://127.0.0.1:8000/health

---

## Run with Docker

Build and run the container:
```bash
docker build -t risk-signal-api .
docker run -p 8000:8000 risk-signal-api
```

Or using Docker Compose:
```bash
docker compose up --build
```

Then open:

- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs

---

## Potential Use Cases

**EM macro / FX desks**  
Monitoring sanctions, energy supply, and banking stress headlines for frontier and emerging markets.

**Bank treasury / ALM**  
Screening daily news for regulatory pressure, banking stress and macro risk signals that may impact liquidity or funding.

**Commodity and energy traders**  
Tracking energy-related risk tags such as `energy_supply_risk_eu` or `energy_price_risk_global` across time.

**Corporate risk & strategy teams**  
Running quick risk sweeps on specific topics (e.g. sanctions, regulation, trade disruptions) before investment committees or board meetings.

**Research / data teams**  
Using the API as a simple feature generator for more advanced machine learning models or dashboards.

---

## Deployment (Railway Example)

1. Push the repository to GitHub.
2. On Railway, create a new project → **New Service** → **Deploy from GitHub repo**.
3. Railway will detect the Dockerfile and build the image.
4. Set an environment variable in the Railway service:
```
PORT=8000
```

5. Ensure the container command binds to `0.0.0.0` using the `PORT` variable:
```bash
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```

6. Deploy and open the generated public URL:
   - `/health` for health checks
   - `/docs` for interactive API docs

---

## Tech Stack

- Python 3.10+
- FastAPI
- Pydantic
- Uvicorn
- Docker