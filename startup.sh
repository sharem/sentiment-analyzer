#!/bin/bash

# Sentiment Analyzer Startup Script
# This script starts all components of the sentiment analysis pipeline

set -e  # Exit on any error

echo "🚀 Starting Sentiment Analyzer Pipeline..."
echo "=========================================="

# Check if we're in the right directory
if [ ! -f "data_pipeline/docker-compose.yml" ]; then
    echo "❌ Error: Please run this script from the sentiment-analyzer project root"
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: Virtual environment not detected"
    echo "   Attempting to activate sentiment-analyzer venv..."
    
    if [ -f "sentiment-analyzer/bin/activate" ]; then
        source sentiment-analyzer/bin/activate
        echo "✅ Virtual environment activated"
    else
        echo "❌ Error: Virtual environment not found at sentiment-analyzer/bin/activate"
        echo "   Please create it with: python -m venv sentiment-analyzer"
        exit 1
    fi
fi

# Verify package is installed
if ! python -c "import backend.app" 2>/dev/null; then
    echo "⚠️  Package not installed. Installing in editable mode..."
    pip install -e . || {
        echo "❌ Failed to install package"
        exit 1
    }
    echo "✅ Package installed successfully"
fi

# Function to check if a service is running
check_service() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=1

    echo "⏳ Waiting for $service_name to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://127.0.0.1:$port" > /dev/null 2>&1 || \
           curl -s "http://localhost:$port" > /dev/null 2>&1; then
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
    local module_path=$1
    local service_name=$2
    local log_file="logs/$(basename ${module_path##*.}).log"
    
    echo "🐍 Starting $service_name..."
    mkdir -p logs
    
    # Run as Python module to use proper imports
    nohup python -m "$module_path" > "$log_file" 2>&1 &
    local pid=$!
    echo "   $service_name started with PID $pid (logs: $log_file)"
}

# 1. Start Docker services (Kafka + Zookeeper)
echo "🐳 Starting Docker services..."

if ! docker info > /dev/null 2>&1; then
    echo "   Starting Docker service..."
    sudo service docker start
    sleep 3
    
    if ! docker info > /dev/null 2>&1; then
        echo "❌ Failed to start Docker service"
        exit 1
    fi
fi

cd data_pipeline

if docker-compose ps -q 2>/dev/null | grep -q .; then
    echo "   Stopping existing containers..."
    docker-compose down --volumes --remove-orphans
else
    echo "   No existing containers to stop"
fi

echo "   Starting Kafka and Zookeeper..."
docker-compose up -d

cd ..

echo "⏳ Waiting for Kafka to be ready..."
sleep 15

# 2. Start Backend (Flask API)
start_python_service "backend.app" "Backend API"
sleep 5

check_service "Backend API" "5000" || {
    echo "❌ Backend failed to start. Check logs/app.log"
    exit 1
}

# 3. Start Consumer
start_python_service "data_pipeline.consumer" "Sentiment Consumer"
sleep 3

# 4. Start Producer
start_python_service "data_pipeline.producer" "Reddit Producer"
sleep 3

# 5. Start Frontend
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
        echo "⚠️  Failed to start Frontend. Check logs/frontend.log"
    fi
fi
cd ..

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
echo "   • Backend API:        http://127.0.0.1:5000"
echo "   • Frontend Dashboard: http://localhost:4321"
echo ""
echo "📝 Log Files:"
echo "   • Backend:    logs/app.log"
echo "   • Consumer:   logs/consumer.log"
echo "   • Producer:   logs/producer.log"
echo "   • Frontend:   logs/frontend.log"
echo ""
echo "🔍 Monitor the pipeline:"
echo "   curl http://127.0.0.1:5000/api/stats"
echo ""
echo "🛑 To stop all services, run: ./shutdown.sh"
echo ""
