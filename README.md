# Sentiment Analyzer

A real-time sentiment analysis pipeline that streams Reddit comments through a message broker, performs NLP sentiment analysis, and displays results in a live web dashboard. Select a subreddit or post to start monitoring. The dashboard appears once a target is chosen, and switching targets resets the data for a clean session.

> **Note:** This project is built for educational purposes. It serves as a hands-on exploration of Hexagonal Architecture (Ports & Adapters), FastAPI, and working with Python and Redis/Kafka. As a result, some design decisions may prioritise learning and experimentation over production-ready conventions. 🙇‍♀️

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

The backend follows **Hexagonal Architecture (Ports & Adapters)** with strict dependency direction: domain → application → infrastructure.

- **Domain** — pure entities and value objects; no ports, no framework imports
- **Application** — use cases + driven ports (ABCs); depends only on domain
- **Infrastructure** — adapters implementing the ports; depends on application and domain

Swapping SQLite → PostgreSQL, Kafka → Redis, or TextBlob → another NLP library requires changing only the adapter, not the business logic.

> **Note:** Kafka is intentionally overengineered for this scale. Redis Pub/Sub is the default; Kafka is included for exploration.

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
│   │   │   ├── message_broker.py        # Port: publish/consume on a transport + BrokerError
│   │   │   ├── monitor_repository.py    # Port: read/write the active monitor target
│   │   │   ├── sentiment_analyzer.py    # Port: classify text → (Sentiment, polarity)
│   │   │   ├── live_stream.py           # Port: subscribe to the SSE event stream
│   │   │   └── subreddit_resolver.py    # Port: resolve a subreddit name + SubredditNotFoundError
│   │   ├── raw_comment.py               # DTO: inbound wire shape shared by producer/consumer
│   │   ├── process_comment_service.py   # Use case: analyse a RawComment and persist it
│   │   └── configure_monitor_service.py # Use case: validate and switch the monitor target
│   ├── infrastructure/
│   │   ├── api/
│   │   │   ├── app.py                   # FastAPI adapter — routes and middleware
│   │   │   ├── requests.py              # Pydantic request models
│   │   │   ├── responses.py             # Pydantic response models
│   │   │   └── exception_handlers.py    # Centralised HTTP exception handlers
│   │   ├── messaging/
│   │   │   ├── channels.py              # Shared topic/channel name constants
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
