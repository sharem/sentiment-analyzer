"""FastAPI application to serve sentiment analysis data."""

import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.application.configure_monitor_use_case import ConfigureMonitorUseCase
from backend.application.ports.comment_repository import CommentRepository
from backend.application.ports.live_stream import LiveEventStream
from backend.application.ports.subreddit_resolver import SubredditNotFoundError
from backend.domain.comment import Comment
from backend.infrastructure.api import exception_handlers
from backend.infrastructure.api.auth import router as auth_router
from backend.infrastructure.api.exception_handlers import HealthCheckError
from backend.infrastructure.api.requests import MonitorConfigRequest
from backend.infrastructure.api.responses import (
    CommentResponse,
    HealthResponse,
    MonitorConfigResponse,
    SentimentCountsResponse,
)
from backend.application.ports.monitor_repository import MonitorRepository
from backend.infrastructure.composition import get_redis_client
from backend.infrastructure.fastapi_deps import get_configure_monitor_use_case, get_live_stream, get_monitor_repository, get_repository
from backend.infrastructure.messaging.redis_comment_publisher import COMMENTS_LIVE_CHANNEL

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:4321").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(HealthCheckError, exception_handlers.health_check_error_handler)
app.add_exception_handler(StarletteHTTPException, exception_handlers.log_http_exception)
app.add_exception_handler(RequestValidationError, exception_handlers.log_validation_error)
app.add_exception_handler(Exception, exception_handlers.handle_exception)

app.include_router(auth_router)


@app.middleware("http")
async def security_headers(request: Request, call_next) -> Any:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


@app.get("/api/monitor", response_model=MonitorConfigResponse)
def get_monitor(monitor_repo: MonitorRepository = Depends(get_monitor_repository)) -> MonitorConfigResponse:
    target = monitor_repo.get()
    return MonitorConfigResponse(subreddit=target.subreddit, post_id=target.post_id)


@app.post("/api/monitor", response_model=MonitorConfigResponse)
def set_monitor(
    body: MonitorConfigRequest,
    use_case: ConfigureMonitorUseCase = Depends(get_configure_monitor_use_case),
) -> MonitorConfigResponse:
    try:
        target = use_case.execute(body.subreddit, body.post_id)
    except SubredditNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return MonitorConfigResponse(subreddit=target.subreddit, post_id=target.post_id)


@app.get("/api/stream")
async def stream(
    live_stream: LiveEventStream = Depends(get_live_stream),
) -> StreamingResponse:
    async def event_generator():
        async for data in live_stream.subscribe(COMMENTS_LIVE_CHANNEL):
            if data is None:
                yield ": keepalive\n\n"
            else:
                yield f"event: comment\ndata: {json.dumps(data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/sentiment", response_model=SentimentCountsResponse)
def sentiment_data(repo: CommentRepository = Depends(get_repository)) -> dict[str, int]:
    return repo.get_sentiment_counts()


@app.get("/api/comments", response_model=list[CommentResponse])
def comments(
    limit: int = Query(default=10, ge=1, le=100),
    repo: CommentRepository = Depends(get_repository),
) -> list[Comment]:
    return repo.get_recent_comments(limit)


@app.get("/health", response_model=HealthResponse)
def health(
    repo: CommentRepository = Depends(get_repository),
    redis_client=Depends(get_redis_client),
) -> HealthResponse:
    failures: list[str] = []
    try:
        repo.get_sentiment_counts()
    except Exception as e:
        failures.append(f"sqlite: {e}")
    try:
        redis_client.ping()
    except Exception as e:
        failures.append(f"redis: {e}")
    if failures:
        reason = "; ".join(failures)
        logger.exception("Health check failed: %s", reason)
        raise HealthCheckError(reason)
    return HealthResponse(status="healthy")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("ENV") == "development"
    host = "127.0.0.1" if debug else "0.0.0.0"
    uvicorn.run("backend.infrastructure.api.app:app", host=host, port=port, reload=debug)
