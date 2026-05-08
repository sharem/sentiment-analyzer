import { useState, useRef, useCallback, useEffect } from 'react';
import SentimentChart from './SentimentChart.jsx';
import RecentComments from './RecentComments.jsx';
import MonitorControl from './MonitorControl.jsx';
import './Dashboard.css';

export default function Dashboard() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [activeTarget, setActiveTarget] = useState(null);
  const pendingCount = useRef(0);

  useEffect(() => {
    fetch('/api/monitor')
      .then(r => r.json())
      .then(data => { if (data.subreddit) setActiveTarget(data); })
      .catch(() => {});
  }, []);

  const handleComponentRefreshed = useCallback(() => {
    pendingCount.current -= 1;
    if (pendingCount.current <= 0) setIsRefreshing(false);
  }, []);

  function handleRefreshAll() {
    if (isRefreshing) return;
    pendingCount.current = 2;
    setIsRefreshing(true);
    setRefreshKey(k => k + 1);
  }

  function handleTargetChanged(target) {
    setActiveTarget(target);
    pendingCount.current = 2;
    setIsRefreshing(true);
    setRefreshKey(k => k + 1);
  }

  if (!activeTarget) {
    return (
      <div className="dashboard-setup">
        <MonitorControl onTargetChanged={handleTargetChanged} isSetup />
      </div>
    );
  }

  return (
    <div className="dashboard-wrapper">
      <MonitorControl onTargetChanged={handleTargetChanged} activeTarget={activeTarget} />

      <div className="dashboard-controls">
        <button
          onClick={handleRefreshAll}
          disabled={isRefreshing}
          className="dashboard-refresh-button"
        >
          {isRefreshing ? 'Refreshing...' : 'Refresh Now'}
        </button>
      </div>

      <div className="dashboard-grid">
        <div className="panel-section">
          <SentimentChart
            refreshKey={refreshKey}
            onRefreshed={handleComponentRefreshed}
            subreddit={activeTarget.subreddit}
          />
        </div>
        <div className="panel-section">
          <RecentComments
            refreshKey={refreshKey}
            onRefreshed={handleComponentRefreshed}
            subreddit={activeTarget.subreddit}
          />
        </div>
      </div>
    </div>
  );
}
