import os
import time
import uuid
from contextlib import asynccontextmanager

import structlog
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

load_dotenv()

from app.routers import analytics, cards, forecast, goals, settings, subscriptions, transactions
from app.scheduler.jobs import start_scheduler

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
log = structlog.get_logger()
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield


app = FastAPI(title="Finance Bot API", version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["X-API-Key", "Content-Type"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    rid = str(uuid.uuid4())[:8]
    start = time.perf_counter()
    log.info("req.start", rid=rid, method=request.method, path=request.url.path)
    response = await call_next(request)
    ms = round((time.perf_counter() - start) * 1000)
    log.info("req.end", rid=rid, status=response.status_code, ms=ms)
    return response


app.include_router(transactions.router, prefix="/api/transactions", tags=["transactions"])
app.include_router(cards.router, prefix="/api/cards", tags=["cards"])
app.include_router(subscriptions.router, prefix="/api/subscriptions", tags=["subscriptions"])
app.include_router(goals.router, prefix="/api/goals", tags=["goals"])
app.include_router(forecast.router, prefix="/api/forecast", tags=["forecast"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])


@app.get("/health")
def health():
    return {"status": "ok"}
