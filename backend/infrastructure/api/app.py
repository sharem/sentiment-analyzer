"""FastAPI application to serve sentiment analysis data."""

import logging
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.domain.comment import Comment
from backend.domain.comment_repository import CommentRepository
from backend.infrastructure.api import exception_handlers
from backend.infrastructure.api.exception_handlers import HealthCheckError
from backend.infrastructure.api.schemas import (
    CommentResponse,
    HealthResponse,
    SentimentCountsResponse,
    StatsResponse,
)
from backend.infrastructure.repositories import comment_repository as _repo

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


def get_repository() -> CommentRepository:
    return _repo


@app.middleware("http")
async def security_headers(request: Request, call_next) -> Any:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


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
def health(repo: CommentRepository = Depends(get_repository)) -> HealthResponse:
    try:
        repo.get_sentiment_counts()
        return HealthResponse(status="healthy")
    except Exception as e:
        logger.exception("Health check failed: %s", str(e))
        raise HealthCheckError(str(e))


@app.get("/api/stats", response_model=StatsResponse)
def stats(repo: CommentRepository = Depends(get_repository)) -> dict[str, Any]:
    return repo.get_stats()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("ENV") == "development"
    host = "127.0.0.1" if debug else "0.0.0.0"
    uvicorn.run("backend.infrastructure.api.app:app", host=host, port=port, reload=debug)
