"""Flask application to serve sentiment analysis data."""

import logging
import os

from dataclasses import asdict

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

from backend.infrastructure.repositories import comment_repository

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Security configurations
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", os.urandom(24))
app.config["DEBUG"] = os.getenv("FLASK_ENV") == "development"

# Configure CORS more securely
allowed_origins = os.getenv("CORS_ORIGINS", "").split(",")
CORS(app, origins=allowed_origins, supports_credentials=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Routes
@app.route("/api/sentiment")
def sentiment_data():
    """Endpoint to get sentiment analysis counts."""
    try:
        return jsonify(comment_repository.get_sentiment_counts())
    except Exception as e:
        logger.exception("Error in sentiment endpoint: %s", str(e))
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/comments")
def comments():
    """Endpoint to get recent comments with sentiment."""
    try:
        # Validate and parse limit parameter
        limit_param = request.args.get("limit", "10")
        try:
            limit = int(limit_param)
            if limit < 1:
                return (
                    jsonify({"error": "Limit must be a positive integer"}),
                    400,
                )
            # Cap at reasonable maximum to prevent abuse
            limit = min(limit, 100)
        except ValueError:
            return (
                jsonify(
                    {"error": "Invalid limit parameter: must be an integer"}
                ),
                400,
            )
        comments = comment_repository.get_recent_comments(limit)
        return jsonify([asdict(c) for c in comments])
    except Exception as e:
        logger.exception("Error in comments endpoint: %s", str(e))
        return jsonify({"error": "Internal server error"}), 500


@app.route("/health")
def health():
    """Health check for load balancer / monitoring."""
    try:
        comment_repository.get_sentiment_counts()
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        logger.error("Health check failed: %s", str(e))
        return jsonify({"status": "unhealthy", "error": str(e)}), 503


@app.route("/api/stats")
def stats():
    """Endpoint to get overall statistics."""
    try:
        return jsonify(comment_repository.get_stats())
    except Exception as e:
        logger.exception("Error in stats endpoint: %s", str(e))
        return jsonify({"error": "Internal server error"}), 500


@app.after_request
def security_headers(response):
    """Add security headers to all responses."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


@app.errorhandler(404)
def not_found(_error):
    """Handle 404 Not Found errors."""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server errors."""
    logger.exception("Internal error: %s", str(error))
    return jsonify({"error": "Internal server error"}), 500


# Application entry point
if __name__ == "__main__":
    # Configuration from environment variables with sensible defaults
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_ENV") == "development"

    # Use environment variable for host configuration
    # Default to localhost in development, 0.0.0.0 in production
    default_host = "127.0.0.1" if debug else "0.0.0.0"
    host = os.getenv("FLASK_RUN_HOST", default_host)

    logger.info("Starting Flask app on %s:%s (debug=%s)", host, port, debug)
    app.run(debug=debug, port=port, host=host)
