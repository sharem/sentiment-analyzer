#!/bin/bash

# Sentiment Analyzer Startup Script
# This script starts all components of the sentiment analysis pipeline

set -e  # Exit on any error

echo "🚀 Starting Sentiment Analyzer Pipeline..."
echo "=========================================="

# Check if we're in the right directory
if [ ! -f "kafka/docker-compose.yml" ]; then
    echo "❌ Error: Please run this script from the sentiment-analyzer project root"
    exit 1
fi

# Function to check if a service is running
check_service() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=1

    echo "⏳ Waiting for $service_name to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://localhost:$port" > /dev/null 2>&1; then
            echo "✅ $service_name is ready!"
            return 0
        fi
        echo "   Attempt $attempt/$max_attempts - waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "❌ $service_name failed to start after $max_attempts attempts"
    return 1
}

# Function to start a Python service in background
start_python_service() {
    local script_name=$1
    local service_name=$2
    local log_file="logs/$(basename ${script_name%.py}).log"
    
    echo "🐍 Starting $service_name..."
    mkdir -p logs
    
    if [ "$script_name" = "app.py" ]; then
        cd backend
        nohup python $script_name > "../$log_file" 2>&1 &
        cd ..
    else
        nohup python $script_name > "$log_file" 2>&1 &
    fi
    
    echo "   $service_name started with PID $! (logs: $log_file)"
}

# 1. Start Docker services (Kafka + Zookeeper)
echo "🐳 Starting Docker services..."
sudo service docker start 2>/dev/null || true
cd kafka
docker-compose down --volumes --remove-orphans > /dev/null 2>&1 || true
docker-compose up -d
cd ..

# Wait for Kafka to be ready
echo "⏳ Waiting for Kafka to be ready..."
sleep 15

# 2. Start Backend (Flask API)
start_python_service "app.py" "Backend API"
sleep 5

# Check if backend is ready (using || to handle failure explicitly)
check_service "Backend API" "5000" || {
    echo "❌ Backend failed to start. Check logs/app.log"
    exit 1
}

# 3. Start Consumer
start_python_service "kafka/consumer.py" "Sentiment Consumer"
sleep 3

# 4. Start Producer
start_python_service "kafka/producer.py" "Reddit Producer"
sleep 3

# 5. Start Frontend (if not already running)
echo "🌐 Starting Frontend..."
cd frontend
if lsof -Pi :4321 -sTCP:LISTEN -t >/dev/null; then
    echo "   Frontend is already running on port 4321"
else
    nohup npm run dev > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    sleep 2
    if lsof -Pi :4321 -sTCP:LISTEN -t >/dev/null; then
        echo "   Frontend started with PID $FRONTEND_PID (logs: logs/frontend.log)"
    else
        echo "⚠️  Failed to start Frontend. Port 4321 may already be in use or there was an error. Check logs/frontend.log."
    fi
fi
cd ..

# Wait for frontend to be ready (allow failure for frontend)
sleep 10
if ! check_service "Frontend" "4321"; then
    echo "⚠️  Frontend may not be ready yet, but continuing..."
fi

echo ""
echo "🎉 Sentiment Analyzer Pipeline Started Successfully!"
echo "=================================================="
echo ""
echo "📊 Services Running:"
echo "   • Kafka & Zookeeper: http://localhost:9092"
echo "   • Backend API:        http://localhost:5000"
echo "   • Frontend Dashboard: http://localhost:4321"
echo ""
echo "📝 Log Files:"
echo "   • Backend:    logs/app.log"
echo "   • Consumer:   logs/consumer.log"
echo "   • Producer:   logs/producer.log"
echo "   • Frontend:   logs/frontend.log"
echo ""
echo "🔍 Monitor the pipeline:"
echo "   curl http://localhost:5000/api/stats"
echo ""
echo "🛑 To stop all services, run: ./shutdown.sh"
echo ""
