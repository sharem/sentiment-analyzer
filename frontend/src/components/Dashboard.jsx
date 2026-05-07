import { useState, useRef, useCallback } from 'react';
import SentimentChart from './SentimentChart.jsx';
import RecentComments from './RecentComments.jsx';
import './Dashboard.css';

export default function Dashboard() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const pendingCount = useRef(0);

  const handleComponentRefreshed = useCallback(() => {
    pendingCount.current -= 1;
    if (pendingCount.current <= 0) {
      setIsRefreshing(false);
    }
  }, []);

  function handleRefreshAll() {
    if (isRefreshing) return;
    pendingCount.current = 2;
    setIsRefreshing(true);
    setRefreshKey(k => k + 1);
  }

  return (
    <div className="dashboard-wrapper">
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
          <SentimentChart refreshKey={refreshKey} onRefreshed={handleComponentRefreshed} />
        </div>
        <div className="panel-section">
          <RecentComments refreshKey={refreshKey} onRefreshed={handleComponentRefreshed} />
        </div>
      </div>
    </div>
  );
}
