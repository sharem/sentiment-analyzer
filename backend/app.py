from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import json

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
    return jsonify(sentiment_counts)

@app.route("/api/comments")
def comments():
    return jsonify(recent_comments)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
