#!/bin/bash

# Sentiment Analyzer Shutdown Script
# This script stops all components of the sentiment analysis pipeline

echo "🛑 Shutting Down Sentiment Analyzer Pipeline..."
echo "==============================================="

# Function to kill processes by name pattern
kill_processes() {
    local pattern=$1
    local service_name=$2
    
    echo "🔪 Stopping $service_name..."
    pkill -f "$pattern" 2>/dev/null || true
    sleep 2
    
    # Force kill if still running
    pkill -9 -f "$pattern" 2>/dev/null || true
    echo "   $service_name stopped"
}

# 1. Stop Python services
kill_processes "python.*kafka/producer.py" "Reddit Producer"
kill_processes "python.*kafka/consumer.py" "Sentiment Consumer"
kill_processes "python.*app.py" "Backend API"

# 2. Stop Frontend (Node.js)
echo "🌐 Stopping Frontend..."
if lsof -Pi :4321 -sTCP:LISTEN -t >/dev/null; then
    kill $(lsof -Pi :4321 -sTCP:LISTEN -t) 2>/dev/null || true
    echo "   Frontend stopped"
else
    echo "   Frontend was not running"
fi

# Also kill any npm processes
pkill -f "npm run dev" 2>/dev/null || true

# 3. Stop Docker services
echo "🐳 Stopping Docker services..."
cd kafka 2>/dev/null || true
docker-compose down --volumes --remove-orphans > /dev/null 2>&1 || true
cd .. 2>/dev/null || true
echo "   Kafka & Zookeeper stopped"

# 4. Clean up log files (optional)
read -p "🗑️  Remove log files? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf logs/
    echo "   Log files removed"
fi

# 5. Clean up temporary data files
if [ -f "/tmp/sentiment_data.json" ]; then
    read -p "🗑️  Remove sentiment data cache? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f /tmp/sentiment_data.json
        echo "   Sentiment data cache removed"
    fi
fi

echo ""
echo "✅ Sentiment Analyzer Pipeline Stopped Successfully!"
echo "=================================================="
echo ""
echo "🔄 To start the pipeline again, run: ./startup.sh"
echo ""
