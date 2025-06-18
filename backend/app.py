""" Flask application to serve sentiment analysis data. """

import os
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from dummy_data import recent_comments

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Security configurations
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))
app.config['DEBUG'] = os.getenv('FLASK_ENV') == 'development'

# Configure CORS more securely
allowed_origins = os.getenv("CORS_ORIGINS", "").split(",")
CORS(app, origins=allowed_origins, supports_credentials=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_sentiment_counts():
    """Calculate sentiment counts from recent comments."""
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for comment in recent_comments:
        sentiment = comment.get("sentiment", "neutral")
        if sentiment in counts:
            counts[sentiment] += 1
    return counts

# Routes
@app.route("/api/sentiment")
def sentiment_data():
    """Endpoint to get sentiment analysis counts."""
    try:
        return jsonify(get_sentiment_counts())
    except (ValueError, KeyError) as e:
        logger.exception("Error in sentiment endpoint: %s", str(e))
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/comments")
def comments():
    """Endpoint to get recent comments with sentiment."""
    try:
        # Add pagination to prevent data exposure
        limit = min(int(request.args.get('limit', 10)), 50)
        return jsonify(recent_comments[:limit])
    except (ValueError, TypeError) as e:
        logger.exception("Error in comments endpoint: %s", str(e))
        return jsonify({"error": "Internal server error"}), 500

@app.after_request
def security_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
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
    # More secure production settings
    port = int(os.getenv('PORT', '5000'))
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(debug=debug, port=port, host="0.0.0.0")
