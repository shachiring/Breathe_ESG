import { useState } from 'react';
import { uploadFile } from '../api';

const SOURCES = [
  {
    id: 'SAP',
    title: 'SAP Export',
    desc: 'Upload a flat-file CSV export from SAP (EKPO/MSEG). Supports German and English headers, semicolon or comma delimiters.',
    accept: '.csv,.txt',
    icon: '📊',
  },
  {
    id: 'UTILITY',
    title: 'Utility Portal',
    desc: 'Upload a CSV from your electricity utility portal (e.g. PG&E, Duke Energy). Expects meter readings with billing periods.',
    accept: '.csv',
    icon: '⚡',
  },
  {
    id: 'TRAVEL',
    title: 'Corporate Travel (Navan)',
    desc: 'Upload a JSON export from Navan / Concur. Expects booking-level detail with categories (FLIGHT, HOTEL, GROUND, RAIL).',
    accept: '.json',
    icon: '✈️',
  },
];

export default function UploadSection({ onUploadComplete }) {
  const [results, setResults] = useState({});
  const [uploading, setUploading] = useState({});

  const handleFile = async (sourceId, file) => {
    setUploading((p) => ({ ...p, [sourceId]: true }));
    setResults((p) => ({ ...p, [sourceId]: null }));

    try {
      // Using tenant_id=1 (Acme Corp demo)
      const res = await uploadFile(file, sourceId, 1);
      setResults((p) => ({
        ...p,
        [sourceId]: {
          ok: true,
          msg: `✓ ${res.created} records created (${res.flagged} flagged)`,
        },
      }));
      onUploadComplete?.();
    } catch (err) {
      setResults((p) => ({
        ...p,
        [sourceId]: { ok: false, msg: `✗ ${err.message}` },
      }));
    } finally {
      setUploading((p) => ({ ...p, [sourceId]: false }));
    }
  };

  return (
    <section>
      <div className="section-header">
        <h2 className="section-title">Ingest Data</h2>
      </div>

      <div className="upload-section">
        {SOURCES.map((src) => (
          <div key={src.id} className="upload-card">
            <div className="upload-card-title">
              {src.icon} {src.title}
            </div>
            <div className="upload-card-desc">{src.desc}</div>

            <div
              className={`dropzone ${uploading[src.id] ? 'active' : ''}`}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const file = e.dataTransfer.files[0];
                if (file) handleFile(src.id, file);
              }}
            >
              <div className="dropzone-icon">📁</div>
              <div>
                {uploading[src.id]
                  ? 'Uploading…'
                  : 'Drag & drop or click to browse'}
              </div>
              <input
                type="file"
                accept={src.accept}
                onChange={(e) => {
                  const file = e.target.files[0];
                  if (file) handleFile(src.id, file);
                }}
              />
            </div>

            {results[src.id] && (
              <div className={`toast ${results[src.id].ok ? 'success' : 'error'}`}>
                {results[src.id].msg}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
