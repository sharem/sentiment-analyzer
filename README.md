# Sentiment Analyzer

A real-time sentiment analysis pipeline that fetches comments (currently only from Reddit), processes them through Kafka, performs sentiment analysis, and displays results in a web dashboard.

## 🏗️ Architecture

```
Reddit API → Producer → Kafka → Consumer → Backend API → Frontend Dashboard
```

## 📁 Project Structure

```
sentiment-analyzer/
├── data_pipeline/              # Data pipeline components
│   ├── producer.py             # Reddit comment producer
│   ├── consumer.py             # Sentiment analysis consumer
│   ├── docker-compose.yml     # Kafka & Zookeeper services
│   └── README.md               # Pipeline-specific documentation
├── backend/                    # Flask API server
│   ├── app.py                  # Main API endpoints
│   ├── data_service.py         # Data storage service
│   └── tests/                  # Backend test suite
│       ├── __init__.py
│       ├── app_test.py
│       ├── data_service_test.py
│       └── README.md
├── frontend/                   # Astro/React dashboard
│   ├── src/components/         # React components
│   │   ├── SentimentChart.jsx  # Pie chart visualization
│   │   └── RecentComments.jsx  # Recent comments display
│   └── src/pages/index.astro   # Main dashboard page
├── .github/workflows/          # CI/CD pipeline
│   └── pylint.yml             # GitHub Actions workflow
├── startup.sh                  # Start all services
├── shutdown.sh                 # Stop all services
├── status.sh                   # Check service status
└── logs/                       # Service log files
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 16+
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
   # Install Python package
   pip install -e .
   
   # Install frontend dependencies
   cd frontend
   npm install
   cd ..
   ```

3. **Configure Reddit API:**
   ```bash
   # Create .env file with your Reddit credentials
   echo "REDDIT_CLIENT_ID=your_client_id" > .env
   echo "REDDIT_CLIENT_SECRET=your_client_secret" >> .env
   echo "REDDIT_USER_AGENT=sentiment-analyzer-bot" >> .env
   ```

### Running the Application

**Start everything with one command:**
```bash
./startup.sh
```

**Access the application:**
- 🌐 **Frontend Dashboard**: http://localhost:4321
- 🔧 **Backend API**: http://localhost:5000
- 📊 **API Stats**: http://localhost:5000/api/stats

**Stop everything:**
```bash
./shutdown.sh
```

**Check status:**
```bash
./status.sh
```

## 🔧 Components

### Data Pipeline (`data_pipeline/`)
- **Producer**: Fetches Reddit comments from r/AskReddit and sends to Kafka
- **Consumer**: Processes Kafka messages and performs sentiment analysis using TextBlob
- **Infrastructure**: Docker-based Kafka and Zookeeper setup

### Backend (`backend/`)
- **Flask API**: Serves sentiment data and recent comments
- **Data Service**: Thread-safe file-based data storage
- **Endpoints**: `/api/sentiment`, `/api/comments`, `/api/stats`

### Frontend (`frontend/`)
- **Astro Framework**: Static site generation with React components
- **Auto-refresh**: Updates every 10 seconds automatically
- **Visualizations**: Interactive pie charts and comment lists

## 📊 Features

- ✅ **Real-time Processing**: Live Reddit comments → Sentiment analysis
- ✅ **Auto-refresh Dashboard**: Updates every 10 seconds
- ✅ **Sentiment Classification**: Positive, Negative, Neutral analysis
- ✅ **Visual Analytics**: Interactive pie charts and data displays
- ✅ **Scalable Architecture**: Kafka-based message queue
- ✅ **Easy Management**: One-command startup/shutdown
- ✅ **Comprehensive Monitoring**: Status checking and logging

## 🛠️ Management Scripts

### Primary Scripts

**🚀 startup.sh:**
```bash
./startup.sh
```
- Starts Docker services (Kafka & Zookeeper)
- Launches Backend API (Flask)
- Starts Sentiment Consumer
- Starts Reddit Producer
- Launches Frontend Dashboard
- Creates log files for all components

**🛑 shutdown.sh:**
```bash
./shutdown.sh
```
- Stops all Python services (Producer, Consumer, Backend)
- Stops Frontend (Node.js)
- Stops Docker services (Kafka & Zookeeper)
- Optionally cleans up log files and data cache

**📊 status.sh:**
```bash
./status.sh
```
- Shows status of all running services
- Displays port usage and PIDs
- Shows API statistics and data counts
- Lists log files and their sizes


### Development Testing

**Run all tests:**
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test categories
pytest -m unit          # Fast unit tests
pytest -m integration   # Integration tests
pytest -m persistence   # File I/O tests
pytest -m threading     # Concurrency tests

# Run with coverage
pytest --cov=backend

# Run specific test file
pytest backend/tests/data_service_test.py

# Run specific test class
pytest backend/tests/data_service_test.py::TestAddComments
```

### API Testing

```bash
# Check sentiment data
curl http://localhost:5000/api/sentiment

# Get recent comments
curl http://localhost:5000/api/comments

# View statistics
curl http://localhost:5000/api/stats
```

### Manual Component Control (Advanced)

**If you need to run components individually:**

```bash
# Start Kafka infrastructure only
cd data_pipeline && docker-compose up -d

# Start backend only
python -m backend.app

# Start consumer only
python -m data_pipeline.consumer

# Start producer only
python -m data_pipeline.producer

# Start frontend only
cd frontend && npm run dev
```

## 📈 Monitoring

### Log Management
- **Backend**: `logs/app.log`
- **Consumer**: `logs/consumer.log`
- **Producer**: `logs/producer.log`
- **Frontend**: `logs/frontend.log`

### Service Health
```bash
# Quick health check
./status.sh

# Watch logs in real-time
tail -f logs/app.log
tail -f logs/consumer.log

# Monitor API responses
watch -n 5 'curl -s http://localhost:5000/api/stats | jq'
```

### Data Storage
- **Sentiment Data**: `/tmp/sentiment_data.json`
- **Service Status**: Real-time via `./status.sh`

## ⚙️ Configuration

- **Reddit Subreddit**: Edit `data_pipeline/producer.py` to change source subreddit
- **Refresh Interval**: Modify frontend components for different update frequencies
- **Sentiment Thresholds**: Adjust TextBlob polarity thresholds in `data_pipeline/consumer.py`
- **Service Ports**: Modify port assignments in respective service files

## 🔄 Troubleshooting

### Common Issues

1. **Package not installed:**
   ```bash
   # Verify installation
   python -c "import backend.app; print('OK')"
   
   # Reinstall if needed
   pip install -e .
   ```

2. **Scripts won't execute:**
   ```bash
   chmod +x startup.sh shutdown.sh status.sh
   ```

3. **Services won't start:**
   ```bash
   ./status.sh  # Check what's running
   sudo lsof -i :4321,5000,9092  # Check port conflicts
   ```

4. **No Reddit data:**
   ```bash
   # Check producer logs
   tail -f logs/producer.log
   # Verify API credentials in .env
   ```

5. **Frontend not updating:**
   ```bash
   # Check backend API
   curl http://localhost:5000/api/stats
   # Check frontend logs
   tail -f logs/frontend.log
   ```

6. **Docker issues:**
   ```bash
   sudo service docker start
   cd data_pipeline && docker-compose logs
   ```

### Quick Fixes

**Reset everything:**
```bash
./shutdown.sh
# Answer 'y' to remove logs and data
./startup.sh
```

**Restart specific component:**
```bash
# Example: Restart just the backend
pkill -f "python.*backend.app"
python -m backend.app
```

## 🧑‍💻 Development

### Virtual Environment (Recommended)

For development, use a virtual environment to isolate dependencies:

```bash
# Using venv (built-in)
python -m venv sentiment-analyzer
source sentiment-analyzer/bin/activate  # On Windows: sentiment-analyzer\Scripts\activate

# Then install the package
pip install -e ".[dev]"
```

**Other options:** [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/), [conda](https://docs.conda.io/), [pyenv](https://github.com/pyenv/pyenv)

### Development Dependencies

```bash
# Install all dev dependencies including testing tools
pip install -e ".[dev]"
```

### Code Quality

```bash
# Format code
black backend/ data_pipeline/

# Lint code
pylint backend/ data_pipeline/

# Type checking
mypy backend/ data_pipeline/
```

## 📝 License

Apache License 2.0 - See [LICENSE](LICENSE) for details.

---

<div align="center">

**Made with ❤️ by [sharem](https://github.com/sharem)**

</div>