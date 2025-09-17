import { useEffect, useState } from 'react';
import './RecentComments.css';

export default function RecentComments() {
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isAutoRefreshing, setIsAutoRefreshing] = useState(false);

  const apiUrl = '/api/comments';

  const fetchComments = async (isManual = false) => {
    try {
      if (isManual) {
        setLoading(true);
        setError(null);
      } else {
        setIsAutoRefreshing(true);
      }
      
      const response = await fetch(`${apiUrl}?limit=10`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const commentsData = await response.json();
      console.log('Received comments:', commentsData);
      
      // Validate data structure
      if (!Array.isArray(commentsData)) {
        throw new Error('Invalid data format received');
      }

      setComments(commentsData);
      setLastUpdated(new Date());
    } catch (error) {
      console.error("Error fetching comments:", error);
      setError(error.message);
    } finally {
      setLoading(false);
      setIsAutoRefreshing(false);
    }
  };

  useEffect(() => {
    // Initial fetch
    fetchComments(true);
    
    // Set up automatic refresh every 10 seconds
    const interval = setInterval(() => {
      fetchComments(false);
    }, 10000);
    
    return () => clearInterval(interval);
  }, []);

  const getSentimentClass = (sentiment) => {
    switch (sentiment?.toLowerCase()) {
      case 'positive':
        return 'positive';
      case 'negative':
        return 'negative';
      case 'neutral':
        return 'neutral';
      default:
        return 'unknown';
    }
  };

  const getSentimentIcon = (sentiment) => {
    switch (sentiment?.toLowerCase()) {
      case 'positive':
        return '😊';
      case 'negative':
        return '😞';
      case 'neutral':
        return '😐';
      default:
        return '❓';
    }
  };

  // Loading state
  if (loading && comments.length === 0) {
    return (
      <div className="recent-comments-container">
        <div className="recent-comments-header">
          <h3 className="recent-comments-title">Recent Comments</h3>
        </div>
        <div className="recent-comments-loading">
          <div className="loading-spinner">
            <p>Loading recent comments...</p>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="recent-comments-container">
        <div className="recent-comments-header">
          <h3 className="recent-comments-title">Recent Comments</h3>
          <button 
            onClick={fetchComments}
            className="recent-comments-refresh-button"
          >
            Retry
          </button>
        </div>
        <div className="recent-comments-error">
          <p className="recent-comments-error-text">
            Failed to load comments: {error}
          </p>
        </div>
      </div>
    );
  }

  // No data state
  if (comments.length === 0) {
    return (
      <div className="recent-comments-container">
        <div className="recent-comments-header">
          <h3 className="recent-comments-title">Recent Comments</h3>
          <button 
            onClick={fetchComments}
            disabled={loading}
            className="recent-comments-refresh-button"
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
        <div className="recent-comments-no-data">
          <p>No comments available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="recent-comments-container">
      <div className="recent-comments-header">
        <h3 className="recent-comments-title">
          Recent Comments
          {isAutoRefreshing && (
            <span className="auto-refresh-indicator"> 🔄</span>
          )}
        </h3>
        <div className="recent-comments-controls">
          {lastUpdated && (
            <span className="last-updated">
              Updated: {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <button 
            onClick={() => fetchComments(true)}
            disabled={loading}
            className="recent-comments-refresh-button"
          >
            {loading ? 'Refreshing...' : 'Refresh Now'}
          </button>
        </div>
      </div>
      
      <div className="recent-comments-list">
        {comments.map((comment, index) => (
          <div key={`${comment.timestamp}-${index}`} className="comment-item">
            <div className="comment-content">
              <p className="comment-text">{comment.text}</p>
              {comment.timestamp && (
                <small className="comment-timestamp">
                  {new Date(comment.timestamp).toLocaleTimeString()}
                </small>
              )}
            </div>
            <div className="comment-sentiment">
              <span 
                className={`sentiment-badge ${getSentimentClass(comment.sentiment)}`}
              >
                <span className="sentiment-icon">
                  {getSentimentIcon(comment.sentiment)}
                </span>
                {comment.sentiment || 'Unknown'}
                {comment.polarity !== undefined && (
                  <span className="polarity-score">
                    ({comment.polarity.toFixed(2)})
                  </span>
                )}
              </span>
            </div>
          </div>
        ))}
      </div>
      
      <div className="auto-refresh-info">
        <small>📡 Auto-refreshes every 10 seconds</small>
      </div>
      
      {loading && comments.length > 0 && (
        <div className="recent-comments-updating">
          <p>🔄 Updating...</p>
        </div>
      )}
    </div>
  );
}
