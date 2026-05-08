import { useEffect, useState, useCallback, useMemo } from 'react';
import { Pie } from 'react-chartjs-2';
import 'chart.js/auto';
import './SentimentChart.css';

export default function SentimentChart({ subreddit = null }) {
  const [sentimentCounts, setSentimentCounts] = useState({
    positive: 0,
    negative: 0,
    neutral: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchSentimentData = useCallback(async () => {
    try {
      const response = await fetch('/api/sentiment');
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const sentimentData = await response.json();
      setSentimentCounts({
        positive: sentimentData.positive || 0,
        negative: sentimentData.negative || 0,
        neutral: sentimentData.neutral || 0
      });
      setLastUpdated(new Date());
      setLoading(false);
      setError(null);
    } catch (error) {
      console.error("Error fetching sentiment data:", error);
      setError(error.message);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSentimentData();
  }, [fetchSentimentData]);

  useEffect(() => {
    const es = new EventSource('/api/stream');

    es.addEventListener('comment', (e) => {
      const comment = JSON.parse(e.data);
      setSentimentCounts(prev => ({
        ...prev,
        [comment.sentiment]: (prev[comment.sentiment] ?? 0) + 1,
      }));
      setLastUpdated(new Date());
    });

    return () => es.close();
  }, [subreddit]);

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
      animateScale: true,
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
        <p>Waiting for comments{subreddit ? ` from r/${subreddit}` : ''}…</p>
      </div>
    );
  }

  return (
    <div className="sentiment-chart-container">
      <div className="sentiment-chart-header">
        <h3 className="sentiment-chart-title">
          Sentiment Analysis
          {subreddit && <span className="chart-subreddit-badge">r/{subreddit}</span>}
        </h3>
        {lastUpdated && (
          <span className="last-updated">Updated: {lastUpdated.toLocaleTimeString()}</span>
        )}
      </div>
      <div className="sentiment-chart-wrapper">
        <Pie data={chartData} options={chartOptions} />
      </div>
      <div className="auto-refresh-info">
        <small>⚡ Live updates via server-sent events</small>
      </div>
    </div>
  );
}
