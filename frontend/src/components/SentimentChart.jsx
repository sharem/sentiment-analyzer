import { useEffect, useState } from 'react';
import { Pie } from 'react-chartjs-2';
import Chart from 'chart.js/auto';
import './SentimentChart.css';

export default function SentimentChart() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const apiUrl = import.meta.env.VITE_API_URL 
    ? `${import.meta.env.VITE_API_URL}/api/sentiment`
    : 'http://localhost:5000/api/sentiment';

  useEffect(() => {
    const fetchSentimentData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        console.log('Fetching from URL:', apiUrl);
        
        const response = await fetch(apiUrl);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const sentimentData = await response.json();
        console.log('Received data:', sentimentData);
        
        // Validate data structure
        if (!sentimentData || typeof sentimentData !== 'object') {
          throw new Error('Invalid data format received');
        }

        const chartData = {
          labels: ['Positive', 'Negative', 'Neutral'],
          datasets: [{
            data: [
              sentimentData.positive || 0, 
              sentimentData.negative || 0, 
              sentimentData.neutral || 0
            ],
            backgroundColor: ['#10B981', '#EF4444', '#F59E0B'],
            hoverBackgroundColor: ['#059669', '#DC2626', '#D97706'],
            borderWidth: 2,
            borderColor: '#ffffff'
          }]
        };
        
        setData(chartData);
      } catch (error) {
        console.error("Error fetching sentiment data:", error);
        setError(error.message);
      } finally {
        setLoading(false);
      }
    };

    fetchSentimentData();
  }, [apiUrl]);
  
  const chartOptions = {
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
      animateScale: true
    }
  };

  const refreshData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(apiUrl);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const sentimentData = await response.json();
      const chartData = {
        labels: ['Positive', 'Negative', 'Neutral'],
        datasets: [{
          data: [
            sentimentData.positive || 0, 
            sentimentData.negative || 0, 
            sentimentData.neutral || 0
          ],
          backgroundColor: ['#10B981', '#EF4444', '#F59E0B'],
          hoverBackgroundColor: ['#059669', '#DC2626', '#D97706'],
          borderWidth: 2,
          borderColor: '#ffffff'
        }]
      };
      setData(chartData);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  // Loading state
  if (loading) {
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
          onClick={refreshData}
          className="sentiment-chart-button"
        >
          Retry
        </button>
      </div>
    );
  }

  // No data state
  if (!data || data.datasets[0].data.every(value => value === 0)) {
    return (
      <div className="sentiment-chart-container sentiment-chart-no-data">
        <p>No sentiment data available</p>
      </div>
    );
  }

  return (
    <div className="sentiment-chart-container">
      <div className="sentiment-chart-header">
        <h3 className="sentiment-chart-title">Sentiment Analysis</h3>
        <button 
          onClick={refreshData}
          disabled={loading}
          className="sentiment-chart-refresh-button"
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>
      <div className="sentiment-chart-wrapper">
        <Pie data={data} options={chartOptions} />
      </div>
    </div>
  );
}
