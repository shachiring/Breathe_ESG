import { useEffect, useState, useCallback } from 'react';
import { fetchRecords, bulkReview } from '../api';

const SCOPE_MAP = {
  SCOPE_1: { label: 'Scope 1', cls: 'scope1' },
  SCOPE_2: { label: 'Scope 2', cls: 'scope2' },
  SCOPE_3: { label: 'Scope 3', cls: 'scope3' },
};

const SOURCE_MAP = {
  SAP: { label: 'SAP', cls: 'sap' },
  UTILITY: { label: 'Utility', cls: 'utility' },
  TRAVEL: { label: 'Travel', cls: 'travel' },
};

const STATUS_MAP = {
  PENDING: 'pending',
  APPROVED: 'approved',
  REJECTED: 'rejected',
  FLAGGED: 'flagged',
};

export default function ReviewDashboard() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(new Set());
  const [viewPayload, setViewPayload] = useState(null);
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);

  // Filters
  const [filterSource, setFilterSource] = useState('');
  const [filterScope, setFilterScope] = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  const loadRecords = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page };
      if (filterSource) params.source_type = filterSource;
      if (filterScope) params.scope = filterScope;
      if (filterStatus) params.status = filterStatus;
      const data = await fetchRecords(params);
      setRecords(data.results || []);
      setHasNext(!!data.next);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [page, filterSource, filterScope, filterStatus]);

  useEffect(() => {
    loadRecords();
  }, [loadRecords]);

  // Reset page when filters change
  useEffect(() => { setPage(1); }, [filterSource, filterScope, filterStatus]);

  const toggleSelect = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === records.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(records.map((r) => r.id)));
    }
  };

  const handleBulkAction = async (action) => {
    if (selected.size === 0) return;
    try {
      await bulkReview([...selected], action);
      setSelected(new Set());
      loadRecords();
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const fmt = (n) =>
    n != null ? Number(n).toLocaleString(undefined, { maximumFractionDigits: 2 }) : '—';

  return (
    <section>
      <div className="section-header">
        <h2 className="section-title">Review Dashboard</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className="btn btn-success btn-sm"
            disabled={selected.size === 0}
            onClick={() => handleBulkAction('APPROVED')}
          >
            ✓ Approve ({selected.size})
          </button>
          <button
            className="btn btn-danger btn-sm"
            disabled={selected.size === 0}
            onClick={() => handleBulkAction('REJECTED')}
          >
            ✗ Reject ({selected.size})
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="filter-bar">
        <select
          id="filter-source"
          value={filterSource}
          onChange={(e) => setFilterSource(e.target.value)}
        >
          <option value="">All Sources</option>
          <option value="SAP">SAP</option>
          <option value="UTILITY">Utility</option>
          <option value="TRAVEL">Travel</option>
        </select>
        <select
          id="filter-scope"
          value={filterScope}
          onChange={(e) => setFilterScope(e.target.value)}
        >
          <option value="">All Scopes</option>
          <option value="SCOPE_1">Scope 1</option>
          <option value="SCOPE_2">Scope 2</option>
          <option value="SCOPE_3">Scope 3</option>
        </select>
        <select
          id="filter-status"
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="PENDING">Pending</option>
          <option value="FLAGGED">Flagged</option>
          <option value="APPROVED">Approved</option>
          <option value="REJECTED">Rejected</option>
        </select>
      </div>

      {loading ? (
        <div className="loading">Loading records…</div>
      ) : records.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📭</div>
          <div className="empty-state-text">No records match your filters</div>
        </div>
      ) : (
        <>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>
                    <input
                      type="checkbox"
                      checked={selected.size === records.length && records.length > 0}
                      onChange={toggleAll}
                    />
                  </th>
                  <th>Source</th>
                  <th>Scope</th>
                  <th>Activity</th>
                  <th>Quantity</th>
                  <th>Unit</th>
                  <th>CO₂e (kg)</th>
                  <th>Period</th>
                  <th>Status</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {records.map((r) => {
                  const scopeInfo = SCOPE_MAP[r.scope] || { label: r.scope, cls: '' };
                  const sourceInfo = SOURCE_MAP[r.source_type] || { label: r.source_type, cls: '' };
                  const statusCls = STATUS_MAP[r.status] || 'pending';
                  return (
                    <tr key={r.id}>
                      <td>
                        <input
                          type="checkbox"
                          checked={selected.has(r.id)}
                          onChange={() => toggleSelect(r.id)}
                        />
                      </td>
                      <td>
                        <span className={`source-badge ${sourceInfo.cls}`}>
                          {sourceInfo.label}
                        </span>
                      </td>
                      <td>
                        <span className={`scope-badge ${scopeInfo.cls}`}>
                          {scopeInfo.label}
                        </span>
                      </td>
                      <td>{r.activity_type}</td>
                      <td style={{ fontVariantNumeric: 'tabular-nums' }}>
                        {fmt(r.quantity)}
                      </td>
                      <td style={{ color: 'var(--text-muted)' }}>{r.unit}</td>
                      <td style={{ fontVariantNumeric: 'tabular-nums' }}>
                        {fmt(r.emissions_kg_co2e)}
                      </td>
                      <td style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>
                        {r.period_start || '—'}
                      </td>
                      <td>
                        <span className={`badge ${statusCls}`}>
                          {r.status}
                        </span>
                        {r.flag_reason && (
                          <div
                            style={{
                              fontSize: '0.7rem',
                              color: 'var(--accent-pink)',
                              marginTop: 3,
                              maxWidth: 180,
                              lineHeight: 1.3,
                            }}
                          >
                            ⚠ {r.flag_reason}
                          </div>
                        )}
                      </td>
                      <td>
                        <button
                          className="btn btn-ghost btn-sm"
                          onClick={() => setViewPayload(r)}
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="pagination">
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              ← Prev
            </button>
            <span>Page {page}</span>
            <button disabled={!hasNext} onClick={() => setPage((p) => p + 1)}>
              Next →
            </button>
          </div>
        </>
      )}

      {/* Payload Modal */}
      {viewPayload && (
        <div className="modal-overlay" onClick={() => setViewPayload(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-title">
              Original Payload — {viewPayload.activity_type}
            </div>
            <pre>{JSON.stringify(viewPayload.original_payload, null, 2)}</pre>
            {viewPayload.flag_reason && (
              <div className="toast error" style={{ marginTop: 12 }}>
                ⚠ {viewPayload.flag_reason}
              </div>
            )}
            <div className="modal-footer">
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => setViewPayload(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
