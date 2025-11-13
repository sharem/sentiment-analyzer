import { useEffect, useState, useCallback, useMemo } from 'react';
import { Pie } from 'react-chartjs-2';
import Chart from 'chart.js/auto';
import './SentimentChart.css';

export default function SentimentChart() {
  const [sentimentCounts, setSentimentCounts] = useState({
    positive: 0,
    negative: 0,
    neutral: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const apiUrl = '/api/sentiment';

  const fetchSentimentData = useCallback(async (isManual = false) => {
    try {
      setIsRefreshing(true);
      
      if (isManual) {
        setError(null);
      }
            
      const response = await fetch(apiUrl);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const sentimentData = await response.json();
      console.log('Received sentiment data:', sentimentData);
      
      // Validate data structure
      if (!sentimentData || typeof sentimentData !== 'object') {
        throw new Error('Invalid data format received');
      }

      // Update only the counts, not the entire data structure
      setSentimentCounts({
        positive: sentimentData.positive || 0,
        negative: sentimentData.negative || 0,
        neutral: sentimentData.neutral || 0
      });
      
      setLastUpdated(new Date());
      setLoading(false);
    } catch (error) {
      console.error("Error fetching sentiment data:", error);
      setError(error.message);
      setLoading(false);
    } finally {
      setIsRefreshing(false);
    }
  }, [apiUrl]);

  useEffect(() => {
    // Initial fetch
    fetchSentimentData(true);
    
    // Set up automatic refresh every 10 seconds
    const interval = setInterval(() => {
      fetchSentimentData(false);
    }, 10000);
    
    return () => clearInterval(interval);
  }, [fetchSentimentData]);

  // Memoize the chart data structure
  const chartData = useMemo(() => ({
    labels: ['Positive', 'Negative', 'Neutral'],
    datasets: [{
      data: [sentimentCounts.positive, sentimentCounts.negative, sentimentCounts.neutral],
      backgroundColor: ['#10B981', '#EF4444', '#F59E0B'],
      hoverBackgroundColor: ['#059669', '#DC2626', '#D97706'],
      borderWidth: 2,
      borderColor: '#ffffff'
    }]
  }), [sentimentCounts.positive, sentimentCounts.negative, sentimentCounts.neutral]);
  
  const chartOptions = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          padding: 20,
          usePointStyle: true,
          font: {
            size: 12
          }
        }
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            const total = context.dataset.data.reduce((a, b) => a + b, 0);
            const percentage = total > 0 ? ((context.raw / total) * 100).toFixed(1) : 0;
            return `${context.label}: ${context.raw} (${percentage}%)`;
          }
        }
      }
    },
    animation: {
      animateRotate: true,
      animateScale: false,
      duration: 500,
      easing: 'easeInOutQuart'
    }
  }), []);

  const hasNoData = sentimentCounts.positive === 0 && 
                    sentimentCounts.negative === 0 && 
                    sentimentCounts.neutral === 0;

  // Loading state (only on initial load)
  if (loading && hasNoData) {
    return (
      <div className="sentiment-chart-container sentiment-chart-loading">
        <div className="loading-spinner">
          <p>Loading sentiment data...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="sentiment-chart-container sentiment-chart-error">
        <p className="sentiment-chart-error-text">
          Failed to load sentiment data: {error}
        </p>
        <button 
          onClick={() => fetchSentimentData(true)}
          className="sentiment-chart-button"
        >
          Retry
        </button>
      </div>
    );
  }

  // No data state
  if (hasNoData) {
    return (
      <div className="sentiment-chart-container sentiment-chart-no-data">
        <p>No sentiment data available</p>
      </div>
    );
  }

  return (
    <div className="sentiment-chart-container">
      <div className="sentiment-chart-header">
        <h3 className="sentiment-chart-title">
          Sentiment Analysis
          {isRefreshing && (
            <span className="auto-refresh-indicator"> 🔄</span>
          )}
        </h3>
        <div className="sentiment-chart-controls">
          {lastUpdated && (
            <span className="last-updated">
              Updated: {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <button 
            onClick={() => fetchSentimentData(true)}
            disabled={isRefreshing}
            className="sentiment-chart-refresh-button"
          >
            {isRefreshing ? 'Refreshing...' : 'Refresh Now'}
          </button>
        </div>
      </div>
      <div className="sentiment-chart-wrapper">
        <Pie data={chartData} options={chartOptions} />
      </div>
      <div className="auto-refresh-info">
        <small>📡 Auto-refreshes every 10 seconds</small>
      </div>
    </div>
  );
}
