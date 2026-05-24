import { useState } from 'react';
import './index.css';
import StatsBar from './components/StatsBar';
import UploadSection from './components/UploadSection';
import ReviewDashboard from './components/ReviewDashboard';

const TABS = [
  { id: 'dashboard', label: 'Review Dashboard' },
  { id: 'upload', label: 'Ingest Data' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [refreshKey, setRefreshKey] = useState(0);

  const triggerRefresh = () => setRefreshKey((k) => k + 1);

  return (
    <div className="app-container">
      {/* ─── Header ─── */}
      <header className="app-header">
        <div className="header-inner">
          <div className="logo">
            <div className="logo-icon">🌿</div>
            <span>Breathe ESG</span>
          </div>
          <nav className="header-nav">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                className={activeTab === tab.id ? 'active' : ''}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* ─── Main ─── */}
      <main className="main-content">
        <StatsBar key={`stats-${refreshKey}`} />

        {activeTab === 'upload' && (
          <UploadSection onUploadComplete={triggerRefresh} />
        )}

        {activeTab === 'dashboard' && (
          <ReviewDashboard key={`review-${refreshKey}`} />
        )}
      </main>
    </div>
  );
}
