"""FastAPI application to serve sentiment analysis data."""

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.domain.comment import Comment
from backend.domain.comment_repository import CommentRepository
from backend.infrastructure.api import exception_handlers
from backend.infrastructure.api.exception_handlers import HealthCheckError
from backend.infrastructure.api.requests import MonitorConfigRequest
from backend.infrastructure.api.responses import (
    CommentResponse,
    HealthResponse,
    MonitorConfigResponse,
    SentimentCountsResponse,
    StatsResponse,
)
from backend.domain.monitor_repository import MonitorRepository
from backend.infrastructure.dependencies import get_live_stream, get_monitor_repository, get_repository
from backend.infrastructure.messaging.live_stream import LiveEventStream

load_dotenv()

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
def get_monitor(repo: MonitorRepository = Depends(get_monitor_repository)) -> MonitorConfigResponse:
    target = repo.get()
    return MonitorConfigResponse(subreddit=target.subreddit, post_id=target.post_id)


@app.post("/api/monitor", response_model=MonitorConfigResponse)
def set_monitor(
    body: MonitorConfigRequest,
    repo: MonitorRepository = Depends(get_monitor_repository),
) -> MonitorConfigResponse:
    target = repo.set(subreddit=body.subreddit, post_id=body.post_id)
    logger.info(
        f"Monitor target updated: r/{target.subreddit}"
        + (f" post={target.post_id}" if target.post_id else "")
    )
    return MonitorConfigResponse(subreddit=target.subreddit, post_id=target.post_id)


def _matches_filter(event_data: dict, subreddit: str | None) -> bool:
    return subreddit is None or event_data.get("subreddit") == subreddit


@app.get("/api/stream")
async def stream(
    subreddit: str | None = Query(default=None),
    live_stream: LiveEventStream = Depends(get_live_stream),
) -> StreamingResponse:
    async def event_generator():
        async for data in live_stream.subscribe("comments:live"):
            if data is None:
                yield ": keepalive\n\n"
            elif _matches_filter(data, subreddit):
                yield f"event: comment\ndata: {json.dumps(data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/sentiment", response_model=SentimentCountsResponse)
def sentiment_data(
    subreddit: str | None = Query(default=None),
    repo: CommentRepository = Depends(get_repository),
) -> dict[str, int]:
    return repo.get_sentiment_counts(subreddit=subreddit)


@app.get("/api/comments", response_model=list[CommentResponse])
def comments(
    limit: int = Query(default=10, ge=1, le=100),
    subreddit: str | None = Query(default=None),
    repo: CommentRepository = Depends(get_repository),
) -> list[Comment]:
    return repo.get_recent_comments(limit, subreddit=subreddit)


@app.get("/api/stats", response_model=StatsResponse)
def stats(
    subreddit: str | None = Query(default=None),
    repo: CommentRepository = Depends(get_repository),
) -> dict[str, Any]:
    return repo.get_stats(subreddit=subreddit)


@app.get("/health", response_model=HealthResponse)
def health(repo: CommentRepository = Depends(get_repository)) -> HealthResponse:
    try:
        repo.get_sentiment_counts()
        return HealthResponse(status="healthy")
    except Exception as e:
        logger.exception("Health check failed: %s", str(e))
        raise HealthCheckError(str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("ENV") == "development"
    host = "127.0.0.1" if debug else "0.0.0.0"
    uvicorn.run("backend.infrastructure.api.app:app", host=host, port=port, reload=debug)
