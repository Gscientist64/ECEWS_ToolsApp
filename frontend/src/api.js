// frontend/src/api.js
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

// Helper to parse JSON and surface server error messages nicely
const asJson = async (res) => {
  if (!res.ok) {
    let detail = '';
    try {
      const j = await res.json();
      detail = j?.error || j?.message || '';
    } catch {}
    throw new Error(`HTTP ${res.status}${detail ? `: ${detail}` : ''}`);
  }
  return res.json();
};

export const api = {
  // ---------- Auth ----------
  async me() {
    const r = await fetch(`${API_URL}/api/me`, { credentials: 'include' });
    return asJson(r);
  },

  async login(username, password) {
    const r = await fetch(`${API_URL}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ username, password }),
    });
    return asJson(r);
  },

  async signup(payload) {
    const r = await fetch(`${API_URL}/api/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload), // include facility & role in payload
    });
    return asJson(r);
  },

  async logout() {
    const r = await fetch(`${API_URL}/api/logout`, { method: 'POST', credentials: 'include' });
    return asJson(r);
  },

  // ---------- Tools ----------
  async tools(params = {}) {
    const q = new URLSearchParams(params).toString();
    const r = await fetch(`${API_URL}/api/tools?${q}`, { credentials: 'include' });
    return asJson(r);
  },

  async createTool(payload) {
    const r = await fetch(`${API_URL}/api/tools`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload),
    });
    return asJson(r);
  },

  async updateTool(id, payload) {
    const r = await fetch(`${API_URL}/api/tools/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload),
    });
    return asJson(r);
  },

  async deleteTool(id, password) {
    const r = await fetch(`${API_URL}/api/tools/${id}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ password }),
    });
    return asJson(r);
  },

  async toolLogs(id) {
    const r = await fetch(`${API_URL}/api/tools/${id}/logs`, { credentials: 'include' });
    return asJson(r);
  },

  async checkoutTool(id, assignee) {
    const r = await fetch(`${API_URL}/api/tools/${id}/checkout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ assignee }),
    });
    return asJson(r);
  },

  async checkinTool(id) {
    const r = await fetch(`${API_URL}/api/tools/${id}/checkin`, {
      method: 'POST',
      credentials: 'include',
    });
    return asJson(r);
  },

  async importCSV(file) {
    const f = new FormData();
    f.append('file', file);
    const r = await fetch(`${API_URL}/api/tools/import`, {
      method: 'POST',
      body: f,
      credentials: 'include',
    });
    return asJson(r);
  },

  async exportCSV() {
    const r = await fetch(`${API_URL}/api/tools/export`, { credentials: 'include' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.text(); // CSV text
  },

  // ---------- Users / Categories / Catalog ----------
  async users() {
    const r = await fetch(`${API_URL}/api/users`, { credentials: 'include' });
    return asJson(r);
  },

  async categories() {
    const r = await fetch(`${API_URL}/api/categories`, { credentials: 'include' });
    return asJson(r);
  },

  async catalog() {
    const r = await fetch(`${API_URL}/api/catalog`, { credentials: 'include' });
    return asJson(r);
  },

  // ---------- Requests ----------
  async createRequest(items) {
    const r = await fetch(`${API_URL}/api/requests`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ items }),
    });
    return asJson(r);
  },

  // (optional alias if some code still calls createCombinedRequest)
  async createCombinedRequest(items) {
    return this.createRequest(items);
  },

  // Accepts array or { requests: [...] }
  async myRequests() {
    const r = await fetch(`${API_URL}/api/requests`, { credentials: 'include' });
    const j = await asJson(r);
    if (Array.isArray(j)) return j;
    if (j && Array.isArray(j.requests)) return j.requests;
    return [];
  },
    // ---------- Admin ----------
  async adminRequests(status) {
    const qs = status ? `?status=${encodeURIComponent(status)}` : '';
    const r = await fetch(`${API_URL}/api/admin/requests${qs}`, { credentials: 'include' });
    return asJson(r); // returns an array
  },
  async adminApproveRequest(id) {
    const r = await fetch(`${API_URL}/api/admin/requests/${id}/approve`, {
      method: 'POST',
      credentials: 'include',
    });
    return asJson(r);
  },
  async adminRejectRequest(id) {
    const r = await fetch(`${API_URL}/api/admin/requests/${id}/reject`, {
      method: 'POST',
      credentials: 'include',
    });
    return asJson(r);
  },
  async adminEditRequest(id, lines) {
    const r = await fetch(`${API_URL}/api/admin/requests/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ lines }),
    });
    return asJson(r);
  },
  async adminDeleteRequest(id) {
    const r = await fetch(`${API_URL}/api/admin/requests/${id}`, {
      method: 'DELETE',
      credentials: 'include',
    });
    return asJson(r);
  },
};
