""" Flask application to serve sentiment analysis data. """

from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)

load_dotenv()

# Dummy in-memory sentiment data
sentiment_counts = {"positive": 10, "neutral": 5, "negative": 2}
recent_comments = [
    {"text": "I love this!", "sentiment": "positive"},
    {"text": "Not great.", "sentiment": "negative"},
]

@app.route("/api/sentiment")
def sentiment():
    """Endpoint to get sentiment analysis counts."""
    return jsonify(sentiment_counts)

@app.route("/api/comments")
def comments():
    """Endpoint to get recent comments with sentiment."""
    return jsonify(recent_comments)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
