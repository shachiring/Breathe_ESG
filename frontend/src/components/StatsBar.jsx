import { useEffect, useState } from 'react';
import { fetchStats } from '../api';

export default function StatsBar() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetchStats().then(setStats).catch(console.error);
  }, []);

  if (!stats) return <div className="loading">Loading dashboard…</div>;

  const scopeTotal =
    (stats.scope_emissions_kg?.SCOPE_1 || 0) +
    (stats.scope_emissions_kg?.SCOPE_2 || 0) +
    (stats.scope_emissions_kg?.SCOPE_3 || 0);

  const pct = (val) => (scopeTotal > 0 ? ((val / scopeTotal) * 100).toFixed(1) : 0);
  const fmt = (n) => n.toLocaleString(undefined, { maximumFractionDigits: 1 });

  const cards = [
    { label: 'Total Records', value: stats.total_records, cls: 'blue' },
    { label: 'Pending Review', value: stats.pending, cls: 'amber' },
    { label: 'Approved', value: stats.approved, cls: 'green' },
    { label: 'Rejected', value: stats.rejected, cls: 'red' },
    { label: 'Flagged', value: stats.flagged, cls: 'purple' },
  ];

  return (
    <section>
      <div className="stats-grid">
        {cards.map((c) => (
          <div key={c.label} className={`stat-card ${c.cls}`}>
            <div className="stat-label">{c.label}</div>
            <div className="stat-value">{c.value}</div>
          </div>
        ))}
      </div>

      {/* Scope breakdown bar */}
      {scopeTotal > 0 && (
        <div style={{ marginBottom: 32 }}>
          <div className="stat-label" style={{ marginBottom: 6 }}>
            Total Emissions: {fmt(scopeTotal)} kg CO₂e
          </div>
          <div className="scope-bar">
            <div
              className="scope-bar-segment s1"
              style={{ width: `${pct(stats.scope_emissions_kg.SCOPE_1)}%` }}
            />
            <div
              className="scope-bar-segment s2"
              style={{ width: `${pct(stats.scope_emissions_kg.SCOPE_2)}%` }}
            />
            <div
              className="scope-bar-segment s3"
              style={{ width: `${pct(stats.scope_emissions_kg.SCOPE_3)}%` }}
            />
          </div>
          <div className="scope-legend">
            <span className="scope-legend-item">
              <span className="scope-legend-dot" style={{ background: 'var(--accent-blue)' }} />
              Scope 1: {fmt(stats.scope_emissions_kg.SCOPE_1)} kg
            </span>
            <span className="scope-legend-item">
              <span className="scope-legend-dot" style={{ background: 'var(--accent-cyan)' }} />
              Scope 2: {fmt(stats.scope_emissions_kg.SCOPE_2)} kg
            </span>
            <span className="scope-legend-item">
              <span className="scope-legend-dot" style={{ background: 'var(--accent-purple)' }} />
              Scope 3: {fmt(stats.scope_emissions_kg.SCOPE_3)} kg
            </span>
          </div>
        </div>
      )}
    </section>
  );
}
