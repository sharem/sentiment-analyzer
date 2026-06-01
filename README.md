# Sentiment Analyzer

A real-time sentiment analysis pipeline that streams Reddit comments through a message broker, performs NLP sentiment analysis, and displays results in a live web dashboard. Select a subreddit or post to start monitoring. The dashboard appears once a target is chosen, and switching targets resets the data for a clean session.

> **Note:** This project is built for educational purposes. It serves as a hands-on exploration of Hexagonal Architecture (Ports & Adapters), FastAPI, and working with Python and Redis/Kafka. As a result, some design decisions may prioritise learning and experimentation over production-ready conventions. 🙇‍♀️

## Architecture

```
Reddit API → Producer → [reddit-comments stream] → Consumer → SQLite
              MessageBroker (Redis Streams or Kafka)      ↓
              persisted log · consumer groups · XACK   AnalyseCommentUseCase
                                                          ↓
                                                  RedisCommentPublisher
                                                          ↓
                                                  [comments:live Pub/Sub channel]
                                                          ↓
                                                  FastAPI /api/stream → Browser (SSE)
```

The backend follows **Hexagonal Architecture (Ports & Adapters)** with strict dependency direction: domain → application → infrastructure.

- **Domain** — pure entities and value objects; no ports, no framework imports
- **Application** — use cases + driven ports (ABCs); depends only on domain
- **Infrastructure** — adapters implementing the ports; depends on application and domain

Swapping SQLite → PostgreSQL, Kafka → Redis, or TextBlob → another NLP library requires changing only the adapter, not the business logic.

### Transport choice: Redis Streams vs Pub/Sub

This project deliberately uses **two different Redis transports** for two different jobs.

| Path | Transport | Why |
|---|---|---|
| Producer → Consumer (`reddit-comments`) | **Redis Streams** (XADD / XREADGROUP / XACK) | Persisted log + consumer groups + at-least-once delivery. A restarting or slow consumer doesn't lose comments — they sit in the pending entries list until acknowledged. `MAXLEN ~ 10000` keeps memory bounded. Same semantics as Kafka, which is why the two broker adapters stay symmetric. |
| Consumer → Browser (`comments:live`) | **Redis Pub/Sub** | Fire-and-forget fan-out to SSE clients. Each browser is a short-lived subscriber that doesn't care about history — if it misses a message because it's mid-reconnect, that's acceptable. Pub/Sub keeps the SSE path cheap and trivial. |

Kafka remains available as a drop-in replacement for the pipeline transport (`BROKER=kafka`) — included for exploration, not because the scale requires it.

## Project Structure

```
sentiment-analyzer/
├── backend/
│   ├── domain/                          # Entities and value objects — zero imports
│   │   ├── comment.py                   # Comment entity + Sentiment enum
│   │   ├── monitor_target.py            # MonitorTarget value object
│   │   └── user.py                      # User entity (GitHub-authenticated)
│   ├── application/
│   │   ├── ports/                       # Driven ports (ABCs) — no infrastructure imports
│   │   │   ├── comment_repository.py    # Port: persist and query Comments
│   │   │   ├── comment_publisher.py     # Port: publish a processed Comment
│   │   │   ├── message_broker.py        # Port: publish/consume on a transport + BrokerError
│   │   │   ├── monitor_repository.py    # Port: read/write the active monitor target
│   │   │   ├── oauth_provider.py        # Port: OAuth identity provider (e.g. GitHub)
│   │   │   ├── sentiment_analyzer.py    # Port: classify text → (Sentiment, polarity)
│   │   │   ├── session_store.py         # Port: server-side session storage
│   │   │   ├── live_stream.py           # Port: subscribe to the SSE event stream
│   │   │   ├── subreddit_resolver.py    # Port: resolve a subreddit name + SubredditNotFoundError
│   │   │   └── user_repository.py       # Port: persist authenticated users
│   │   ├── raw_comment.py                       # DTO: inbound wire shape shared by producer/consumer
│   │   ├── analyse_comment_use_case.py          # Use case: analyse a RawComment and persist it
│   │   ├── configure_monitor_use_case.py        # Use case: validate and switch the monitor target
│   │   └── sign_in_with_oauth_use_case.py       # Use case: exchange OAuth code → User + session
│   ├── infrastructure/
│   │   ├── api/
│   │   │   ├── app.py                      # FastAPI adapter — routes and middleware
│   │   │   ├── auth.py                     # Auth router: /auth/github/{login,callback}, /auth/me, /auth/logout
│   │   │   ├── requests.py                 # Pydantic request models
│   │   │   ├── responses.py                # Pydantic response models
│   │   │   └── exception_handlers.py       # Centralised HTTP exception handlers
│   │   ├── auth/
│   │   │   ├── github_oauth_provider.py    # OAuthProvider adapter: GitHub
│   │   │   └── redis_session_store.py      # SessionStore adapter: Redis with TTL
│   │   ├── messaging/
│   │   │   ├── broker_factory.py           # Instantiates pipeline broker from BROKER env var
│   │   │   ├── kafka_broker.py             # Kafka adapter (alternative pipeline transport)
│   │   │   ├── redis_stream_broker.py      # Redis Streams adapter (default pipeline transport)
│   │   │   ├── redis_comment_publisher.py  # Pub/Sub: writes processed comments to comments:live
│   │   │   └── redis_live_event_stream.py  # Pub/Sub: async subscribe for SSE clients
│   │   ├── nlp/
│   │   │   └── textblob_analyzer.py        # Adapter: TextBlobSentimentAnalyzer
│   │   ├── pipeline/
│   │   │   ├── producer.py                 # Reddit → broker (thin adapter)
│   │   │   ├── consumer.py                 # Broker → AnalyseCommentUseCase (thin adapter)
│   │   │   └── topics.py                   # Shared topic name for producer/consumer
│   │   ├── reddit/
│   │   │   └── subreddit_resolver.py       # Adapter: HttpSubredditResolver
│   │   ├── repositories/
│   │   │   ├── sqlite_repository.py        # Adapter: SQLiteCommentRepository
│   │   │   ├── sqlite_user_repository.py   # Adapter: SQLiteUserRepository
│   │   │   └── redis_monitor_repository.py # Adapter: RedisMonitorRepository
│   │   ├── composition.py                  # Framework-free composition root (factories used by every entry point)
│   │   └── fastapi_deps.py                 # FastAPI Depends() wrappers around composition
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

3. **Register a GitHub OAuth app** (for the sign-in feature):

   Go to https://github.com/settings/developers → *New OAuth App*. Use:
   - *Homepage URL:* `http://localhost:4321`
   - *Authorization callback URL:* `http://localhost:4321/auth/github/callback`

   Copy the *Client ID* and generate a *Client Secret*.

4. **Configure environment variables** (create `backend/.env`):
   ```bash
   REDDIT_CLIENT_ID=your_client_id
   REDDIT_CLIENT_SECRET=your_client_secret
   REDDIT_USER_AGENT=sentiment-analyzer-bot

   GITHUB_CLIENT_ID=your_github_oauth_client_id
   GITHUB_CLIENT_SECRET=your_github_oauth_client_secret
   GITHUB_OAUTH_REDIRECT_URI=http://localhost:4321/auth/github/callback
   FRONTEND_URL=http://localhost:4321
   SESSION_TTL_DAYS=7

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
| GitHub OAuth client ID | `GITHUB_CLIENT_ID` | — (required for sign-in) |
| GitHub OAuth client secret | `GITHUB_CLIENT_SECRET` | — (required for sign-in) |
| GitHub OAuth callback URL | `GITHUB_OAUTH_REDIRECT_URI` | `http://localhost:4321/auth/github/callback` |
| Frontend home URL (post-login redirect) | `FRONTEND_URL` | `http://localhost:4321` |
| Session lifetime (days) | `SESSION_TTL_DAYS` | `7` |

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
