#!/bin/bash

# Sentiment Analyzer Shutdown Script
# This script stops all components of the sentiment analysis pipeline

echo "🛑 Shutting Down Sentiment Analyzer Pipeline..."
echo "==============================================="

# Function to kill processes matching a pattern
kill_processes() {
    local pattern=$1
    local service_name=$2
    
    pids=$(pgrep -f "$pattern")
    if [ -n "$pids" ]; then
        echo "Stopping $service_name (PIDs: $pids)..."
        kill $pids 2>/dev/null || true
        sleep 2
        # Force kill if still running
        pids=$(pgrep -f "$pattern")
        if [ -n "$pids" ]; then
            echo "  Force stopping $service_name..."
            kill -9 $pids 2>/dev/null || true
        fi
        echo "  ✓ $service_name stopped"
    else
        echo "  ℹ️  $service_name not running"
    fi
}

# 1. Stop Python services (using module paths now)
kill_processes "python.*-m data_pipeline\.producer" "Reddit Producer"
kill_processes "python.*-m data_pipeline\.consumer" "Sentiment Consumer"
kill_processes "python.*-m backend\.infrastructure\.api\.app" "Backend API"

# 2. Stop frontend
echo ""
kill_processes "node.*astro" "Frontend Dashboard"

# 3. Stop Docker services
echo ""
echo "🐳 Stopping Docker services..."
cd data_pipeline 2>/dev/null || true
docker-compose down --volumes --remove-orphans > /dev/null 2>&1 || true
cd .. 2>/dev/null || true
echo "  ✓ Kafka & Zookeeper stopped"

# 4. Clean up log files
echo ""
echo "🧹 Cleaning up..."
rm -f logs/*.pid 2>/dev/null || true
echo "  ✓ Cleanup complete"

echo ""
echo "✅ All services stopped successfully!"
echo ""
