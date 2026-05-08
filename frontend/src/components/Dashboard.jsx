import { useState, useEffect } from 'react';
import SentimentChart from './SentimentChart.jsx';
import RecentComments from './RecentComments.jsx';
import MonitorControl from './MonitorControl.jsx';
import './Dashboard.css';

export default function Dashboard() {
  const [activeTarget, setActiveTarget] = useState(null);

  useEffect(() => {
    fetch('/api/monitor')
      .then(r => r.json())
      .then(data => { if (data.subreddit) setActiveTarget(data); })
      .catch(() => {});
  }, []);

  function handleTargetChanged(target) {
    setActiveTarget(target);
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
      <div className="dashboard-grid">
        <div className="panel-section">
          <SentimentChart subreddit={activeTarget.subreddit} />
        </div>
        <div className="panel-section">
          <RecentComments subreddit={activeTarget.subreddit} />
        </div>
      </div>
    </div>
  );
}
