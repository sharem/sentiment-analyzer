"""FastAPI application to serve sentiment analysis data."""

import logging
import os
from dataclasses import asdict

from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.infrastructure.repositories import comment_repository

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


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


@app.get("/api/sentiment")
def sentiment_data():
    return comment_repository.get_sentiment_counts()


@app.get("/api/comments")
def comments(limit: int = Query(default=10, ge=1, le=100)):
    return [asdict(c) for c in comment_repository.get_recent_comments(limit)]


@app.get("/health")
def health():
    try:
        comment_repository.get_sentiment_counts()
        return {"status": "healthy"}
    except Exception as e:
        logger.error("Health check failed: %s", str(e))
        return JSONResponse({"status": "unhealthy", "error": str(e)}, status_code=503)


@app.get("/api/stats")
def stats():
    return comment_repository.get_stats()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse({"error": "Invalid request parameters"}, status_code=400)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def handle_exception(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", str(exc))
    return JSONResponse({"error": "Internal server error"}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_ENV") == "development"
    host = "127.0.0.1" if debug else "0.0.0.0"
    uvicorn.run("backend.infrastructure.api.app:app", host=host, port=port, reload=debug)
