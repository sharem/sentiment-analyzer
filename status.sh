#!/bin/bash

# Sentiment Analyzer Status Script
# This script checks the status of all pipeline components

echo "📊 Sentiment Analyzer Pipeline Status"
echo "====================================="

# Function to check if a service is running on a port
check_port() {
    local port=$1
    local service_name=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "✅ $service_name (port $port): RUNNING"
        return 0
    else
        echo "❌ $service_name (port $port): NOT RUNNING"
        return 1
    fi
}

# Function to check if a process is running
check_process() {
    local pattern=$1
    local service_name=$2
    
    if pgrep -f "$pattern" >/dev/null 2>&1; then
        local pid=$(pgrep -f "$pattern" | head -1)
        echo "✅ $service_name (PID $pid): RUNNING"
        return 0
    else
        echo "❌ $service_name: NOT RUNNING"
        return 1
    fi
}

# Function to get API status
check_api_status() {
    echo ""
    echo "🔍 API Status:"
    echo "-------------"
    
    if curl -s http://localhost:5000/health >/dev/null 2>&1; then
        echo "✅ Backend API is responding"
        stats=$(curl -s http://localhost:5000/api/stats 2>/dev/null)
        if [ -n "$stats" ]; then
            echo "   Stats: $stats"
        fi
    else
        echo "❌ Backend API not responding"
    fi
}

# Check Python environment
echo "🐍 Python Environment:"
echo "--------------------"
if [ -n "$VIRTUAL_ENV" ]; then
    echo "✅ Virtual environment active: $VIRTUAL_ENV"
    python_path=$(which python3)
    echo "   Python: $python_path"
else
    echo "ℹ️  Using system Python"
    python_path=$(which python3)
    echo "   Python: $python_path"
fi

# Check if package is installed
if python3 -c "import backend.infrastructure.api.app" 2>/dev/null; then
    echo "✅ sentiment-analyzer package is installed"
else
    echo "❌ sentiment-analyzer package not found"
    echo "   Run: pip install -e ."
fi

# Check Docker services
echo ""
echo "🐳 Docker Services:"
echo "------------------"
cd data_pipeline 2>/dev/null || true
if docker-compose ps | grep -q "Up"; then
    docker-compose ps | grep -E "(kafka|zookeeper)" | while read line; do
        if echo "$line" | grep -q "Up"; then
            service_name=$(echo "$line" | awk '{print $1}')
            echo "✅ $service_name: RUNNING"
        fi
    done
else
    echo "❌ Kafka & Zookeeper: NOT RUNNING"
fi
cd .. 2>/dev/null || true

echo ""
echo "🐍 Python Services:"
echo "------------------"
check_process "python.*-m backend\.infrastructure\.api\.app" "Backend API"
check_process "python.*-m data_pipeline\.consumer" "Sentiment Consumer"
check_process "python.*-m data_pipeline\.producer" "Reddit Producer"

echo ""
echo "🌐 Frontend Service:"
echo "------------------"
check_port "4321" "Frontend Dashboard"

# Check API status if backend is running
if curl -s http://localhost:5000/health >/dev/null 2>&1; then
    check_api_status
fi

echo ""
echo "📁 Log Files:"
echo "------------"
if [ -d "logs" ]; then
    for log_file in logs/*.log; do
        if [ -f "$log_file" ]; then
            size=$(du -h "$log_file" | cut -f1)
            echo "   📄 $log_file ($size)"
        fi
    done
else
    echo "   📁 No log directory found"
fi

echo ""
echo "💾 Data Storage:"
echo "---------------"
if [ -f "/tmp/sentiment_data.json" ]; then
    size=$(du -h "/tmp/sentiment_data.json" | cut -f1)
    echo "   💿 Sentiment data cache: $size"
else
    echo "   📭 No sentiment data cache found"
fi

echo ""
echo "🔧 Quick Commands:"
echo "-----------------"
echo "   Start pipeline:  ./startup.sh"
echo "   Stop pipeline:   ./shutdown.sh"
echo "   View backend:    curl http://localhost:5000/api/stats"
echo "   View frontend:   http://localhost:4321"
echo ""
