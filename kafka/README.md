# Kafka Pipeline Components

This directory contains the Kafka-based messaging components of the sentiment analyzer:

## Files

- **`producer.py`** - Reddit comment producer that fetches comments and sends them to Kafka
- **`consumer.py`** - Kafka consumer that processes messages and performs sentiment analysis
- **`docker-compose.yml`** - Docker Compose configuration for Kafka and Zookeeper services

## Usage

The producer and consumer are automatically managed by the main startup scripts in the project root:

```bash
# From project root
./startup.sh   # Starts all services including Kafka, producer, and consumer
./shutdown.sh  # Stops all services
./status.sh    # Shows status of all components
```

## Manual Usage

If you need to run components individually:

```bash
# Start Kafka infrastructure first
cd kafka
docker-compose up -d
cd ..

# Start producer (from project root, in separate terminal)
python kafka/producer.py

# Start consumer (from project root, in separate terminal)
python kafka/consumer.py
```

## Configuration

- Producer fetches from r/AskReddit by default
- Consumer processes messages and stores results in `/tmp/sentiment_data.json`
- Kafka runs on `localhost:9092`
- Zookeeper runs on `localhost:2181`
