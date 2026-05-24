const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `API error ${res.status}`);
  }
  return res.json();
}

export async function fetchStats(tenantId) {
  const q = tenantId ? `?tenant=${tenantId}` : "";
  return request(`/stats/${q}`);
}

export async function fetchRecords(params = {}) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v) q.set(k, v);
  });
  return request(`/records/?${q.toString()}`);
}

export async function fetchImports(tenantId) {
  const q = tenantId ? `?tenant=${tenantId}` : "";
  return request(`/imports/${q}`);
}

export async function fetchTenants() {
  return request("/tenants/");
}

export async function bulkReview(ids, action, notes = "") {
  return request("/records/bulk_review/", {
    method: "POST",
    body: JSON.stringify({ ids, action, reviewer_notes: notes }),
  });
}

export async function uploadFile(file, sourceType, tenantId) {
  const formData = new FormData();
  formData.append("file", file);
  const url = `${API_BASE}/ingest/?source_type=${sourceType}&tenant_id=${tenantId}`;
  const res = await fetch(url, { method: "POST", body: formData });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Upload failed ${res.status}`);
  }
  return res.json();
}

export async function uploadJson(jsonStr, sourceType, tenantId) {
  const formData = new FormData();
  const blob = new Blob([jsonStr], { type: "application/json" });
  formData.append("file", blob, "travel_data.json");
  const url = `${API_BASE}/ingest/?source_type=${sourceType}&tenant_id=${tenantId}`;
  const res = await fetch(url, { method: "POST", body: formData });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Upload failed ${res.status}`);
  }
  return res.json();
}
