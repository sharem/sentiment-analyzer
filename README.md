# Sentiment Analyzer

A real-time sentiment analysis pipeline that fetches Reddit comments, processes them through Kafka, performs sentiment analysis, and displays results in a web dashboard.

## Architecture

```
Reddit API → Producer → Kafka → Consumer → SQLite → FastAPI → Frontend Dashboard
```

The backend follows **Hexagonal Architecture (Ports & Adapters)**. The domain layer is isolated from infrastructure and can swap adapters without touching business logic — e.g. SQLite → PostgreSQL, or Kafka → Redis Pub/Sub with a one-line change.

> **Note:** Kafka is intentionally overengineered for this scale. It's kept because the `MessageBroker` port makes swapping to Redis a one-liner, which demonstrates the architecture works.

## Project Structure

```
sentiment-analyzer/
├── backend/
│   ├── domain/                         # Core domain — no external dependencies
│   │   ├── comment.py                  # Comment entity + Sentiment value object
│   │   ├── comment_repository.py       # Repository port (ABC)
│   │   └── sentiment_service.py        # Sentiment classification domain service
│   ├── infrastructure/
│   │   ├── api/
│   │   │   ├── app.py                  # FastAPI adapter — routes and middleware
│   │   │   ├── exception_handlers.py   # Centralised exception handlers
│   │   │   └── schemas.py              # Pydantic response models
│   │   ├── messaging/
│   │   │   ├── message_broker.py       # MessageBroker ABC
│   │   │   ├── kafka_broker.py         # Kafka adapter
│   │   │   └── redis_broker.py         # Redis Pub/Sub adapter (swap-in replacement)
│   │   ├── pipeline/
│   │   │   ├── producer.py             # Reddit → broker entry point
│   │   │   └── consumer.py             # broker → domain → repository entry point
│   │   └── repositories/
│   │       └── sqlite_repository.py    # SQLite adapter (repository implementation)
│   └── tests/
│       ├── domain/                     # Domain logic tests
│       └── infrastructure/
│           ├── api/                    # API endpoint tests
│           ├── messaging/              # Broker adapter tests
│           ├── pipeline/               # Producer/consumer entry point tests
│           └── repositories/          # Repository integration tests
├── docker-compose.yml                  # Kafka & Zookeeper services
├── frontend/                           # Astro/React dashboard
│   └── src/
│       ├── components/
│       │   ├── Dashboard.jsx           # Layout wrapper with single refresh control
│       │   ├── SentimentChart.jsx      # Pie chart visualization
│       │   └── RecentComments.jsx      # Recent comments display with fade-in animation
│       └── pages/index.astro
├── .github/workflows/
│   └── lint-and-test.yml
├── startup.sh
├── shutdown.sh
├── status.sh
└── logs/
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- Reddit API credentials (for PRAW)

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/sentiment-analyzer.git
   cd sentiment-analyzer
   ```

2. **Install dependencies:**
   ```bash
   pip install -e ".[dev]"
   cd frontend && npm install && cd ..
   ```

3. **Configure environment variables:**
   ```bash
   # backend/.env
   REDDIT_CLIENT_ID=your_client_id
   REDDIT_CLIENT_SECRET=your_client_secret
   REDDIT_USER_AGENT=sentiment-analyzer-bot
   SECRET_KEY=your_secret_key
   CORS_ORIGINS=http://localhost:4321
   KAFKA_BOOTSTRAP_SERVERS=localhost:9092
   KAFKA_TOPIC=reddit-comments
   PORT=5000
   ENV=development
   ```

### Running the Application

```bash
./startup.sh
```

- Frontend Dashboard: http://localhost:4321
- Backend API: http://localhost:5000
- API Stats: http://localhost:5000/api/stats

```bash
./shutdown.sh   # Stop all services
./status.sh     # Check service status
```

## Components

### Domain (`backend/domain/`)
- **`Comment`** — core entity with text, sentiment, polarity, and timestamp
- **`Sentiment`** — value object (POSITIVE / NEUTRAL / NEGATIVE)
- **`CommentRepository`** — port (ABC) defining the storage contract
- **`sentiment_service`** — domain service: `classify_polarity` and `analyze_sentiment`

### Backend Infrastructure (`backend/infrastructure/`)
- **FastAPI** — HTTP adapter exposing `/api/sentiment`, `/api/comments`, `/api/stats`, `/health`. Auto-generates OpenAPI docs at `/docs`.
- **Pydantic schemas** — `CommentResponse`, `SentimentCountsResponse`, `StatsResponse`, `HealthResponse` define and validate all API response shapes.
- **SQLiteCommentRepository** — repository adapter with circular buffer (100 comments default) and WAL mode
- **MessageBroker** — ABC defining the publish/consume interface (lives alongside its implementations)
- **KafkaBroker** — `MessageBroker` implementation; lazy-initialises producer/consumer with exponential-backoff retry on connect
- **RedisBroker** — drop-in `MessageBroker` implementation using Redis Pub/Sub (requires `pip install redis`)

### Pipeline (`backend/infrastructure/pipeline/`)
- **Producer** — streams Reddit comments from r/AskReddit and publishes via `MessageBroker`
- **Consumer** — consumes via `MessageBroker`, calls `analyze_sentiment` (domain service), persists via repository
- Both accept an optional `broker: MessageBroker` parameter for dependency injection (defaults to `KafkaBroker`)

Swapping Kafka for Redis is a one-line change:
```python
main(broker=RedisBroker())   # requires: pip install redis
```

**`docker-compose.yml`** at project root — Kafka + Zookeeper infrastructure.

### Frontend (`frontend/`)
- **Astro + React** — full-viewport dashboard, auto-refreshes every 10 seconds
- **Dashboard** — layout wrapper with a single "Refresh Now" button that updates both panels simultaneously
- **SentimentChart** — interactive pie chart
- **RecentComments** — live comment feed with staggered fade-in animation on refresh

## Development

### Running Tests

```bash
# All tests with coverage
pytest

# Specific layers
pytest backend/tests/domain/
pytest backend/tests/infrastructure/api/
pytest backend/tests/infrastructure/messaging/
pytest backend/tests/infrastructure/pipeline/
pytest backend/tests/infrastructure/repositories/

# Verbose
pytest -v
```

### Code Quality

```bash
flake8 backend/
```

### Running Components Individually

```bash
# Kafka infrastructure
docker-compose up -d

# Backend API (starts uvicorn)
python -m backend.infrastructure.api.app

# Consumer
python -m backend.infrastructure.pipeline.consumer

# Producer
python -m backend.infrastructure.pipeline.producer

# Frontend
cd frontend && npm run dev
```

## Configuration

| Setting | Location | Default |
|---|---|---|
| Sentiment thresholds | `backend/domain/sentiment_service.py` | ±0.1 polarity |
| Circular buffer size | `SQLiteCommentRepository(max_comments=...)` | 100 |
| Database path | `SENTIMENT_DB_PATH` env var | `sentiment.db` |
| Kafka brokers | `KAFKA_BOOTSTRAP_SERVERS` env var | `localhost:9092` |
| API port | `PORT` env var | `5000` |
| CORS origins | `CORS_ORIGINS` env var | _(none)_ |

## Monitoring

```bash
tail -f logs/app.log
tail -f logs/consumer.log
watch -n 5 'curl -s http://localhost:5000/api/stats | jq'
curl -s http://localhost:5000/health   # quick health check
```

## Troubleshooting

**Package not found:**
```bash
pip install -e ".[dev]"
python -c "import backend.domain; print('OK')"
```

**Port conflicts:**
```bash
sudo lsof -i :4321,5000,9092
```

**No data from Reddit:**
```bash
tail -f logs/producer.log   # Check Reddit API credentials
tail -f logs/consumer.log   # Check Kafka connectivity
```

**Docker/Kafka issues:**
```bash
docker-compose logs
sudo service docker start
```

**Reset everything:**
```bash
./shutdown.sh && ./startup.sh
```

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Made with ❤️ by [sharem](https://github.com/sharem)**

</div>
