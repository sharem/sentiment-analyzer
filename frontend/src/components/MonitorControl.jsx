import { useState } from 'react';
import './MonitorControl.css';

export default function MonitorControl({ onTargetChanged, activeTarget = null, isSetup = false }) {
  const [subredditInput, setSubredditInput] = useState('');
  const [postIdInput, setPostIdInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    const sub = subredditInput.trim();
    if (!sub) return;

    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch('/api/monitor', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subreddit: sub, post_id: postIdInput.trim() || null }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setSubredditInput('');
      setPostIdInput('');
      onTargetChanged?.(data);
    } catch {
      setError('Failed to update — check the subreddit name and try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="monitor-control">
      {isSetup ? (
        <p className="monitor-setup-label">Choose a subreddit or post to start monitoring</p>
      ) : (
        <div className="monitor-status">
          <span className="monitor-dot" />
          <span className="monitor-current-label">
            Monitoring r/<strong>{activeTarget.subreddit}</strong>
            {activeTarget.post_id ? ` · post ${activeTarget.post_id}` : ''}
          </span>
        </div>
      )}

      <form className="monitor-form" onSubmit={handleSubmit}>
        <div className="monitor-inputs">
          <div className="monitor-subreddit-wrap">
            <span className="monitor-prefix">r/</span>
            <input
              type="text"
              value={subredditInput}
              onChange={e => setSubredditInput(e.target.value)}
              placeholder="subreddit"
              className="monitor-input"
              disabled={submitting}
              aria-label="Subreddit name"
            />
          </div>
          <input
            type="text"
            value={postIdInput}
            onChange={e => setPostIdInput(e.target.value)}
            placeholder="post ID (optional)"
            className="monitor-input monitor-input-post"
            disabled={submitting}
            aria-label="Post ID"
          />
          <button
            type="submit"
            className="monitor-button"
            disabled={submitting || !subredditInput.trim()}
          >
            {submitting ? (isSetup ? 'Starting…' : 'Switching…') : (isSetup ? 'Start' : 'Switch')}
          </button>
        </div>
        {error && <p className="monitor-error">{error}</p>}
      </form>
    </div>
  );
}
