from __future__ import annotations

import logging
from typing import Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.status import HTTP_400_BAD_REQUEST
from starlette.exceptions import HTTPException as StarletteHTTPException

from models import RiskSignalRequest, RiskSignalResponse
from logic import compute_risk_signal

# ---------- Logging configuration ----------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("risk-signal-api")


# ---------- FastAPI app ----------

app = FastAPI(
    title="RiskSignal API",
    description="Simple heuristic API that turns news into a risk signal.",
    version="0.2.0",
)


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("RiskSignal API starting up")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("RiskSignal API shutting down")


# ---------- Custom error handlers ----------


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning("Validation error: %s", exc)
    # Return 400 instead of default 422, with a simpler body
    return JSONResponse(
        status_code=HTTP_400_BAD_REQUEST,
        content={
            "error": "Invalid request payload",
            "details": exc.errors(),
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    logger.warning("HTTP error %s: %s", exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail or "HTTP error",
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception("Unhandled error while processing request")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


# ---------- Endpoints ----------


@app.get("/health")
def health_check() -> Dict[str, str]:
    logger.info("Health check ping")
    return {"status": "ok"}


@app.post("/risk-signal", response_model=RiskSignalResponse)
def risk_signal_endpoint(payload: RiskSignalRequest) -> RiskSignalResponse:
    """
    Main endpoint:
    - receives a batch of news items,
    - returns overall risk score and per-item breakdown.
    """
    if not payload.items:
        # Dodatkowe zabezpieczenie (choć Pydantic już to waliduje)
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Request must contain at least one item",
        )

    logger.info(
        "Received /risk-signal request with %d items (focus=%s, horizon_days=%d)",
        len(payload.items),
        payload.focus,
        payload.horizon_days,
    )

    response = compute_risk_signal(
        items=payload.items,
        focus=payload.focus,
        horizon_days=payload.horizon_days,
    )

    logger.info(
        "Computed risk signal: overall_risk_score=%d, risk_level=%s",
        response.overall_risk_score,
        response.risk_level,
    )

    return response
