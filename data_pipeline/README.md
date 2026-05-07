# Data Pipeline

Kafka-based pipeline that streams Reddit comments into the sentiment analyzer.

## Files

- **`producer.py`** — fetches comments from r/AskReddit via PRAW and publishes them to the `reddit-comments` Kafka topic
- **`consumer.py`** — reads from Kafka, calls `analyze_sentiment` from the backend domain, and persists each comment via the repository. Retries the Kafka connection up to 5 times with exponential backoff before exiting.
- **`docker-compose.yml`** — Kafka + Zookeeper infrastructure

## Usage

The pipeline is managed by the root startup scripts:

```bash
./startup.sh    # starts Kafka, consumer, and producer
./shutdown.sh   # stops everything
./status.sh     # shows running services and log locations
```

## Manual Usage

```bash
# Start Kafka infrastructure first
cd data_pipeline && docker-compose up -d && cd ..

# Run consumer (separate terminal)
python -m data_pipeline.consumer

# Run producer (separate terminal)
python -m data_pipeline.producer
```

## Configuration

| Setting | Environment variable | Default |
|---|---|---|
| Kafka brokers | `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` |
| Reddit client ID | `REDDIT_CLIENT_ID` | _(required)_ |
| Reddit client secret | `REDDIT_CLIENT_SECRET` | _(required)_ |
| Reddit user agent | `REDDIT_USER_AGENT` | _(required)_ |

Sentiment thresholds (positive > 0.1, negative < -0.1) are defined in `backend/domain/sentiment_service.py`.
