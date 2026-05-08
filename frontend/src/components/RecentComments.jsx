import { useEffect, useState, useCallback } from 'react';
import './RecentComments.css';

export default function RecentComments({ subreddit = null }) {
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchComments = useCallback(async () => {
    try {
      const response = await fetch('/api/comments?limit=10');
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const commentsData = await response.json();
      if (!Array.isArray(commentsData)) throw new Error('Invalid data format received');
      setComments(commentsData.map(c => ({ ...c, id: c.id || crypto.randomUUID() })));
      setLastUpdated(new Date());
      setLoading(false);
      setError(null);
    } catch (error) {
      console.error("Error fetching comments:", error);
      setError(error.message);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchComments();
  }, [fetchComments]);

  useEffect(() => {
    const es = new EventSource('/api/stream');

    es.addEventListener('comment', (e) => {
      const comment = { ...JSON.parse(e.data), id: crypto.randomUUID() };
      setComments(prev => [comment, ...prev].slice(0, 10));
      setLastUpdated(new Date());
    });

    return () => es.close();
  }, [subreddit]);

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
            onClick={() => fetchComments(true)}
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
        </div>
        <div className="recent-comments-no-data">
          <p>Waiting for comments{subreddit ? ` from r/${subreddit}` : ''}…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="recent-comments-container">
      <div className="recent-comments-header">
        <h3 className="recent-comments-title">
          Recent Comments
          {subreddit && <span className="comments-subreddit-badge">r/{subreddit}</span>}
        </h3>
        {lastUpdated && (
          <span className="last-updated">Updated: {lastUpdated.toLocaleTimeString()}</span>
        )}
      </div>
      
      <div className="recent-comments-list">
        {comments.map((comment) => (
          <div key={comment.id} className="comment-item">
            <div className="comment-content">
              <p className="comment-text">{comment.text}</p>
              <div className="comment-meta">
                {comment.timestamp && (
                  <small className="comment-timestamp">
                    {new Date(comment.timestamp).toLocaleTimeString()}
                  </small>
                )}
                {comment.subreddit && comment.subreddit !== 'unknown' && (
                  <small className="comment-subreddit">r/{comment.subreddit}</small>
                )}
              </div>
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
        <small>⚡ Live updates via server-sent events</small>
      </div>
    </div>
  );
}
