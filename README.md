# Sentiment Analyzer

A real-time sentiment analysis pipeline that streams Reddit comments through a message broker, performs NLP sentiment analysis, and displays results in a live web dashboard. Select a subreddit or specific post to start monitoring — the dashboard appears once a target is chosen, and switching targets clears the data for a clean session.

## Architecture

```
Reddit API → Producer → [reddit-comments topic] → Consumer → SQLite
                MessageBroker (Kafka or Redis)        ↓
                                            ProcessCommentService
                                                      ↓
                                            RedisLiveStream.publish()
                                                      ↓
                                            [comments:live channel]
                                                      ↓
                                            FastAPI /api/stream → Browser (SSE)
```

The backend follows **Hexagonal Architecture (Ports & Adapters)** with a strict three-layer dependency rule: domain imports nothing, application imports only domain, infrastructure imports both.

- **Domain** — pure entities and value objects; no ports, no framework imports
- **Application** — use cases + driven ports (ABCs); depends only on domain
- **Infrastructure** — adapters implementing the ports; depends on application and domain

Swapping SQLite → PostgreSQL, Kafka → Redis, or TextBlob → another NLP library requires changing only the adapter, not the business logic.

> **Note:** Kafka is intentionally overengineered for this scale. Redis Pub/Sub is the default; Kafka is available if you want to explore it.

## Project Structure

```
sentiment-analyzer/
├── backend/
│   ├── domain/                          # Entities and value objects — zero imports
│   │   ├── comment.py                   # Comment entity + Sentiment enum
│   │   └── monitor_target.py            # MonitorTarget value object
│   ├── application/
│   │   ├── ports/                       # Driven ports (ABCs) — no infrastructure imports
│   │   │   ├── comment_repository.py    # Port: persist and query Comments
│   │   │   ├── comment_publisher.py     # Port: publish a processed Comment
│   │   │   ├── monitor_repository.py    # Port: read/write the active monitor target
│   │   │   ├── sentiment_analyzer.py    # Port: classify text → (Sentiment, polarity)
│   │   │   ├── live_stream.py           # Port: subscribe to the SSE event stream
│   │   │   └── subreddit_resolver.py    # Port: resolve a subreddit name + SubredditNotFoundError
│   │   ├── process_comment_service.py   # Use case: analyse a raw comment and persist it
│   │   └── configure_monitor_service.py # Use case: validate and switch the monitor target
│   ├── infrastructure/
│   │   ├── api/
│   │   │   ├── app.py                   # FastAPI adapter — routes and middleware
│   │   │   ├── requests.py              # Pydantic request models
│   │   │   ├── responses.py             # Pydantic response models
│   │   │   └── exception_handlers.py    # Centralised HTTP exception handlers
│   │   ├── messaging/
│   │   │   ├── channels.py              # Shared topic/channel name constants
│   │   │   ├── message_broker.py        # MessageBroker port + BrokerError
│   │   │   ├── broker_factory.py        # Instantiates broker from BROKER env var
│   │   │   ├── kafka_broker.py          # Kafka adapter
│   │   │   ├── redis_broker.py          # Redis Pub/Sub adapter (pipeline transport)
│   │   │   └── redis_live_stream.py     # Adapter: CommentPublisher + LiveEventStream over Redis
│   │   ├── nlp/
│   │   │   └── textblob_analyzer.py     # Adapter: TextBlobSentimentAnalyzer
│   │   ├── pipeline/
│   │   │   ├── producer.py              # Reddit → broker (thin adapter)
│   │   │   └── consumer.py              # Broker → ProcessCommentService (thin adapter)
│   │   ├── reddit/
│   │   │   └── subreddit_resolver.py    # Adapter: HttpSubredditResolver
│   │   ├── repositories/
│   │   │   ├── sqlite_repository.py     # Adapter: SQLiteCommentRepository
│   │   │   └── redis_monitor_repository.py  # Adapter: RedisMonitorRepository
│   │   └── dependencies.py              # DI providers for FastAPI and pipeline
│   └── tests/
│       ├── application/                 # Use case unit tests
│       └── infrastructure/
│           ├── api/                     # API endpoint integration tests
│           ├── messaging/               # Broker adapter tests
│           ├── nlp/                     # Analyser adapter tests
│           ├── pipeline/                # Consumer/producer adapter tests
│           ├── reddit/                  # SubredditResolver adapter tests
│           └── repositories/           # Repository integration tests
├── frontend/                            # Astro + React dashboard
│   └── src/components/
│       ├── Dashboard.jsx                # Layout + active subreddit state
│       ├── MonitorControl.jsx           # Subreddit/post switcher
│       ├── SentimentChart.jsx           # Pie chart — live via SSE
│       └── RecentComments.jsx           # Comment feed — live via SSE
├── docker-compose.yml
├── startup.sh
├── shutdown.sh
└── status.sh
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- Reddit API credentials ([create an app](https://www.reddit.com/prefs/apps))

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/sharem/sentiment-analyzer.git
   cd sentiment-analyzer
   ```

2. **Install dependencies:**
   ```bash
   pip install -e ".[dev]"
   cd frontend && npm install && cd ..
   ```

3. **Configure environment variables** (create `backend/.env`):
   ```bash
   REDDIT_CLIENT_ID=your_client_id
   REDDIT_CLIENT_SECRET=your_client_secret
   REDDIT_USER_AGENT=sentiment-analyzer-bot
   CORS_ORIGINS=http://localhost:4321
   PORT=5000
   ENV=development
   ```

### Running the Application

```bash
./startup.sh
```

`startup.sh` prompts you to choose **Kafka** or **Redis** as the message broker and starts the matching containers.

| Service | URL |
|---|---|
| Frontend Dashboard | http://localhost:4321 |
| Backend API + OpenAPI docs | http://localhost:5000/docs |
| Broker UI (Kafka UI / Redis Commander) | http://localhost:8081 |

```bash
./shutdown.sh   # Stop all services
./status.sh     # Check service status
```

## Components

### Domain (`backend/domain/`)

Pure Python — entities and value objects only, no ports or framework imports.

| File | Purpose |
|---|---|
| `comment.py` | `Comment` entity and `Sentiment` enum |
| `monitor_target.py` | `MonitorTarget` value object |

### Application (`backend/application/`)

**Ports** (`ports/`) — driven port ABCs with no infrastructure dependencies:

| File | Purpose |
|---|---|
| `comment_repository.py` | Persist and query comments |
| `comment_publisher.py` | Broadcast a processed comment |
| `sentiment_analyzer.py` | Classify text into sentiment + polarity |
| `monitor_repository.py` | Read/write the active monitor target |
| `live_stream.py` | Subscribe to the SSE event stream |
| `subreddit_resolver.py` | Resolve a subreddit canonical name; defines `SubredditNotFoundError` |

**Use cases:**
- **`ProcessCommentService`** — given a raw message dict, calls `SentimentAnalyzer`, builds a `Comment`, persists it via `CommentRepository`, and notifies via `CommentPublisher`
- **`ConfigureMonitorService`** — validates a subreddit name via `SubredditResolver`, clears the comment DB, and writes the new target via `MonitorRepository`

### Infrastructure (`backend/infrastructure/`)

**API adapter** — FastAPI routes expose:
- `GET /api/sentiment` — sentiment counts for the current session
- `GET /api/comments` — recent comments (`?limit`, default 10)
- `GET /api/monitor` / `POST /api/monitor` — read/set the active monitor target; POST delegates to `ConfigureMonitorService`
- `GET /api/stream` — SSE stream of live processed comments
- `GET /health` — health check

**Messaging:**
- `MessageBroker` (ABC) + `BrokerError` — broker port; adapters translate transport errors so callers are broker-agnostic
- `KafkaBroker` — exponential-backoff retry on connection
- `RedisBroker` — Redis Pub/Sub as a message queue
- `RedisLiveStream` — implements both `LiveEventStream` (subscribe) and `CommentPublisher` (publish) over the same Redis channel

**Reddit:**
- `HttpSubredditResolver` — implements `SubredditResolver` by calling Reddit's public `about.json` endpoint; returns the canonical display name or raises `SubredditNotFoundError`

**Repositories:**
- `SQLiteCommentRepository` — WAL mode, circular buffer (100 comments)
- `RedisMonitorRepository` — JSON-serialised monitor config stored in Redis

**NLP:**
- `TextBlobSentimentAnalyzer` — implements `SentimentAnalyzer` using TextBlob; polarity thresholds at ±0.1

### Frontend (`frontend/`)

Astro + React. Connects to the SSE endpoint on load via `EventSource`; no polling.

- **MonitorControl** — setup screen on first load; prompts for a subreddit or post to monitor; shows the active target once set with an option to switch
- **SentimentChart** — live pie chart, updates on each SSE event; shows "Waiting for comments…" until the first event arrives
- **RecentComments** — live comment feed, newest first, updates on each SSE event

## Development

### Running Tests

```bash
# All tests with coverage
pytest

# By layer
pytest backend/tests/application/
pytest backend/tests/infrastructure/api/
pytest backend/tests/infrastructure/messaging/
pytest backend/tests/infrastructure/repositories/
```

### Running Components Individually

```bash
# Infrastructure (Redis required)
docker-compose --profile redis up -d

# Backend API
python -m backend.infrastructure.api.app

# Consumer
python -m backend.infrastructure.pipeline.consumer

# Producer
python -m backend.infrastructure.pipeline.producer

# Frontend
cd frontend && npm run dev
```

## Configuration

| Setting | Env var / location | Default |
|---|---|---|
| Message broker | `BROKER` | `redis` |
| Kafka brokers | `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` |
| Redis host | `REDIS_HOST` | `localhost` |
| Redis port | `REDIS_PORT` | `6379` |
| Database path | `SENTIMENT_DB_PATH` | `sentiment.db` |
| Circular buffer size | `SQLiteCommentRepository(max_comments=...)` | `100` |
| Sentiment thresholds | `textblob_analyzer.py` | `±0.1 polarity` |
| Default subreddit | — | None (user must select on first load) |
| API port | `PORT` | `5000` |
| CORS origins | `CORS_ORIGINS` | `http://localhost:4321` |

## Monitoring

```bash
tail -f logs/consumer.log
curl -s http://localhost:5000/health
curl -s http://localhost:5000/api/sentiment | jq
```

## Troubleshooting

**Package not found:**
```bash
pip install -e ".[dev]"
```

**No data appearing:**
```bash
tail -f logs/producer.log   # Check Reddit API credentials and monitor target
tail -f logs/consumer.log   # Check broker connectivity
```

**Port conflicts:**
```bash
sudo lsof -i :4321,5000,6379,9092
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
