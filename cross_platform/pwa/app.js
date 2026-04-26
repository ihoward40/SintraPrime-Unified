/**
 * SintraPrime PWA – Core Application Logic
 * Handles: routing, install prompt, push notifications,
 * background sync, IndexedDB offline storage, SW lifecycle.
 */

'use strict';

// ─── Constants ────────────────────────────────────────────────────────────────
const DB_NAME = 'sintra-db';
const DB_VERSION = 1;
const STORES = { cases: 'cases', deadlines: 'deadlines', queue: 'offline-queue', prefs: 'prefs' };
const API_BASE = window.location.origin + '/api';
const VAPID_PUBLIC_KEY = 'BLx2G3kQ9V8ZvFsYFkX2mU7jH4N1oT6pRwC0A3eDz9L5bM8yXJ1QW6nI0Kh7G2tS4R5VuO8P3iE1l0Bm9Y=';

// ─── App State ─────────────────────────────────────────────────────────────────
const state = {
  currentView: 'dashboard',
  isOnline: navigator.onLine,
  db: null,
  sw: null,
  installPrompt: null,
  notificationPermission: Notification.permission,
  offlineQueue: [],
  stats: { cases: 0, deadlines: 0, agents: 0, docs: 0 },
};

// ─── IndexedDB Setup ──────────────────────────────────────────────────────────
async function initDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onerror = () => reject(req.error);
    req.onsuccess = () => { state.db = req.result; resolve(req.result); };
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORES.cases)) {
        const cs = db.createObjectStore(STORES.cases, { keyPath: 'id' });
        cs.createIndex('status', 'status', { unique: false });
        cs.createIndex('updated', 'updated_at', { unique: false });
      }
      if (!db.objectStoreNames.contains(STORES.deadlines)) {
        const ds = db.createObjectStore(STORES.deadlines, { keyPath: 'id' });
        ds.createIndex('date', 'deadline_date', { unique: false });
        ds.createIndex('case_id', 'case_id', { unique: false });
      }
      if (!db.objectStoreNames.contains(STORES.queue)) {
        db.createObjectStore(STORES.queue, { keyPath: 'id', autoIncrement: true });
      }
      if (!db.objectStoreNames.contains(STORES.prefs)) {
        db.createObjectStore(STORES.prefs, { keyPath: 'key' });
      }
    };
  });
}

async function dbGet(storeName, key) {
  return new Promise((resolve, reject) => {
    const tx = state.db.transaction(storeName, 'readonly');
    const req = tx.objectStore(storeName).get(key);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function dbPut(storeName, value) {
  return new Promise((resolve, reject) => {
    const tx = state.db.transaction(storeName, 'readwrite');
    const req = tx.objectStore(storeName).put(value);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function dbGetAll(storeName) {
  return new Promise((resolve, reject) => {
    const tx = state.db.transaction(storeName, 'readonly');
    const req = tx.objectStore(storeName).getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
}

async function dbDelete(storeName, key) {
  return new Promise((resolve, reject) => {
    const tx = state.db.transaction(storeName, 'readwrite');
    const req = tx.objectStore(storeName).delete(key);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

// ─── Service Worker ────────────────────────────────────────────────────────────
async function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) {
    console.warn('[App] Service Worker not supported');
    return;
  }
  try {
    const reg = await navigator.serviceWorker.register('/service_worker.js', { scope: '/' });
    state.sw = reg;
    console.log('[App] SW registered, scope:', reg.scope);

    // Listen for updates
    reg.addEventListener('updatefound', () => {
      const newSW = reg.installing;
      newSW.addEventListener('statechange', () => {
        if (newSW.state === 'installed' && navigator.serviceWorker.controller) {
          showUpdateBanner();
        }
      });
    });

    // Register background sync
    if ('SyncManager' in window) {
      await reg.sync.register('sintra-offline-queue');
    }

    // Register periodic sync for deadlines
    if ('periodicSync' in reg) {
      try {
        await reg.periodicSync.register('sintra-deadline-check', { minInterval: 4 * 60 * 60 * 1000 });
      } catch (e) { /* Periodic sync may not be granted */ }
    }

    return reg;
  } catch (err) {
    console.error('[App] SW registration failed:', err);
  }
}

// Listen for messages from SW
navigator.serviceWorker?.addEventListener('message', (event) => {
  const { type, action } = event.data || {};
  if (type === 'QUEUE_OFFLINE_ACTION') queueOfflineAction(action);
  if (type === 'PROCESS_OFFLINE_QUEUE') processOfflineQueue();
});

// ─── Install Prompt ────────────────────────────────────────────────────────────
let deferredInstallPrompt = null;

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredInstallPrompt = e;
  state.installPrompt = e;

  // Show install banner after 3 seconds if not already installed
  setTimeout(() => showInstallBanner(), 3000);

  console.log('[App] Install prompt captured');
});

window.addEventListener('appinstalled', () => {
  console.log('[App] PWA installed successfully');
  deferredInstallPrompt = null;
  hideElement('installBanner');
  hideElement('installRow');
  showToast('✅ SintraPrime installed successfully!');
});

function showInstallBanner() {
  const banner = document.getElementById('installBanner');
  if (!banner || deferredInstallPrompt === null) return;
  // Don't show if running standalone
  if (window.matchMedia('(display-mode: standalone)').matches) return;
  banner.classList.remove('hidden');
}

async function triggerInstall() {
  if (!deferredInstallPrompt) {
    console.warn('[App] No install prompt available');
    return;
  }
  deferredInstallPrompt.prompt();
  const { outcome } = await deferredInstallPrompt.userChoice;
  console.log('[App] Install outcome:', outcome);
  deferredInstallPrompt = null;
  hideElement('installBanner');
}

// ─── Push Notifications ────────────────────────────────────────────────────────
async function requestNotificationPermission() {
  if (!('Notification' in window)) {
    showToast('❌ Notifications not supported in this browser');
    return false;
  }
  const perm = await Notification.requestPermission();
  state.notificationPermission = perm;
  if (perm === 'granted') {
    await subscribeToPush();
    showToast('🔔 Notifications enabled');
    return true;
  } else {
    showToast('❌ Notification permission denied');
    const toggle = document.getElementById('notifToggle');
    if (toggle) toggle.checked = false;
    return false;
  }
}

async function subscribeToPush() {
  if (!state.sw) return;
  try {
    const sub = await state.sw.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
    });
    // Send subscription to server
    await apiPost('/push/subscribe', sub.toJSON());
    await dbPut(STORES.prefs, { key: 'pushSubscription', value: sub.toJSON() });
    console.log('[App] Push subscription created');
  } catch (err) {
    console.error('[App] Push subscription failed:', err);
  }
}

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = atob(base64);
  return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)));
}

// ─── Navigation / Routing ──────────────────────────────────────────────────────
function navigateTo(viewId) {
  // Deactivate all views
  document.querySelectorAll('.view').forEach((v) => v.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach((a) => a.classList.remove('active'));

  // Activate target view
  const view = document.getElementById(`view-${viewId}`);
  if (view) view.classList.add('active');

  const tabBtn = document.querySelector(`.tab-btn[data-view="${viewId}"]`);
  if (tabBtn) tabBtn.classList.add('active');

  const navItem = document.querySelector(`.nav-item[data-view="${viewId}"]`);
  if (navItem) navItem.classList.add('active');

  state.currentView = viewId;
  history.pushState({ view: viewId }, '', `#${viewId}`);

  // Load view data
  loadViewData(viewId);

  // Close drawer if open
  closeNavDrawer();
}

function loadViewData(viewId) {
  switch (viewId) {
    case 'dashboard': loadDashboard(); break;
    case 'cases': loadCases(); break;
    case 'deadlines': loadDeadlines(); break;
    case 'settings': loadSettings(); break;
  }
}

// ─── Dashboard ─────────────────────────────────────────────────────────────────
async function loadDashboard() {
  setTimeOfDay();
  await Promise.all([fetchStats(), fetchActivity()]);
}

function setTimeOfDay() {
  const h = new Date().getHours();
  const el = document.getElementById('timeOfDay');
  if (!el) return;
  if (h < 12) el.textContent = 'morning';
  else if (h < 17) el.textContent = 'afternoon';
  else el.textContent = 'evening';
}

async function fetchStats() {
  try {
    const data = await apiGet('/health');
    if (data) {
      updateStat('caseCount', data.stats?.active_cases ?? '—');
      updateStat('deadlineCount', data.stats?.upcoming_deadlines ?? '—');
      updateStat('agentCount', data.stats?.running_agents ?? '—');
      updateStat('docCount', data.stats?.pending_docs ?? '—');
    }
  } catch {
    // Show cached stats from IndexedDB
    const cached = await dbGet(STORES.prefs, 'stats');
    if (cached) {
      updateStat('caseCount', cached.value.cases ?? '—');
      updateStat('deadlineCount', cached.value.deadlines ?? '—');
    }
  }
}

function updateStat(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

async function fetchActivity() {
  const list = document.getElementById('activityList');
  if (!list) return;
  try {
    const data = await apiGet('/activity?limit=5');
    if (data?.items?.length > 0) {
      list.innerHTML = data.items.map((item) => `
        <li class="activity-item">
          <span class="activity-icon">${item.icon || '•'}</span>
          <div>
            <strong>${escapeHtml(item.title)}</strong>
            <small style="color:var(--text-muted)">${item.time || ''}</small>
          </div>
        </li>
      `).join('');
    } else {
      list.innerHTML = '<li class="activity-item loading">No recent activity</li>';
    }
  } catch {
    list.innerHTML = '<li class="activity-item loading">Activity unavailable offline</li>';
  }
}

// ─── Cases ─────────────────────────────────────────────────────────────────────
async function loadCases() {
  const container = document.getElementById('casesList');
  if (!container) return;
  container.innerHTML = '<div class="loading-state">Loading cases...</div>';
  try {
    const data = await apiGet('/cases?status=active');
    const cases = data?.cases || [];
    // Cache in IndexedDB
    for (const c of cases) await dbPut(STORES.cases, c);
    renderCases(cases, container);
  } catch {
    const cached = await dbGetAll(STORES.cases);
    if (cached.length > 0) {
      renderCases(cached, container);
      showToast('📡 Showing cached cases');
    } else {
      container.innerHTML = '<div class="loading-state">No cases available offline</div>';
    }
  }
}

function renderCases(cases, container) {
  if (!cases.length) {
    container.innerHTML = '<div class="loading-state">No active cases</div>';
    return;
  }
  container.innerHTML = cases.map((c) => `
    <div class="card" style="margin-bottom:10px;cursor:pointer" onclick="viewCase('${c.id}')">
      <div style="display:flex;justify-content:space-between;align-items:start">
        <div>
          <strong>${escapeHtml(c.title || c.name || 'Untitled')}</strong>
          <div style="color:var(--text-muted);font-size:13px;margin-top:4px">${escapeHtml(c.matter_number || c.id)}</div>
        </div>
        <span class="status-badge ${c.status === 'active' ? 'online' : ''}" style="font-size:11px">${escapeHtml(c.status || 'Active')}</span>
      </div>
    </div>
  `).join('');
}

// ─── Deadlines ─────────────────────────────────────────────────────────────────
async function loadDeadlines() {
  const container = document.getElementById('deadlinesList');
  if (!container) return;
  container.innerHTML = '<div class="loading-state">Loading deadlines...</div>';
  try {
    const data = await apiGet('/deadlines');
    const deadlines = data?.deadlines || [];
    for (const d of deadlines) await dbPut(STORES.deadlines, d);
    renderDeadlines(deadlines, container);
  } catch {
    const cached = await dbGetAll(STORES.deadlines);
    renderDeadlines(cached, container);
    if (cached.length) showToast('📡 Showing cached deadlines');
  }
}

function renderDeadlines(deadlines, container) {
  if (!deadlines.length) {
    container.innerHTML = '<div class="loading-state">No upcoming deadlines</div>';
    return;
  }
  const sorted = [...deadlines].sort((a, b) => new Date(a.deadline_date) - new Date(b.deadline_date));
  container.innerHTML = sorted.map((d) => {
    const date = new Date(d.deadline_date);
    const daysLeft = Math.ceil((date - Date.now()) / 86400000);
    const urgency = daysLeft <= 1 ? 'danger' : daysLeft <= 7 ? 'warning' : 'success';
    return `
      <div class="card" style="margin-bottom:10px;border-left:3px solid var(--${urgency})">
        <div style="display:flex;justify-content:space-between;align-items:start">
          <div>
            <strong>${escapeHtml(d.title || d.type)}</strong>
            <div style="color:var(--text-muted);font-size:13px;margin-top:4px">${escapeHtml(d.case_name || d.case_id || '')}</div>
          </div>
          <div style="text-align:right">
            <div style="font-size:13px;color:var(--${urgency})">${daysLeft <= 0 ? 'Past due' : daysLeft === 1 ? 'Tomorrow' : `${daysLeft}d`}</div>
            <div style="font-size:12px;color:var(--text-muted)">${date.toLocaleDateString()}</div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// ─── Settings ──────────────────────────────────────────────────────────────────
async function loadSettings() {
  // Cache size
  if (navigator.serviceWorker?.controller) {
    navigator.serviceWorker.controller.postMessage({ type: 'GET_CACHE_SIZE' });
  }

  // Notification toggle state
  const toggle = document.getElementById('notifToggle');
  if (toggle) toggle.checked = state.notificationPermission === 'granted';

  // Install button visibility
  if (window.matchMedia('(display-mode: standalone)').matches) {
    hideElement('installRow');
  }

  // API status
  try {
    await apiGet('/health');
    const badge = document.getElementById('apiStatus');
    if (badge) { badge.textContent = 'Connected'; badge.className = 'status-badge online'; }
  } catch {
    const badge = document.getElementById('apiStatus');
    if (badge) { badge.textContent = 'Offline'; badge.className = 'status-badge offline'; }
  }
}

// ─── API Helpers ───────────────────────────────────────────────────────────────
async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Accept': 'application/json', 'X-SintraPrime-Client': 'pwa' },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function apiPost(path, data) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-SintraPrime-Client': 'pwa' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ─── Offline Queue ─────────────────────────────────────────────────────────────
async function queueOfflineAction(action) {
  action.id = Date.now();
  await dbPut(STORES.queue, action);
  console.log('[App] Action queued:', action.url);
}

async function processOfflineQueue() {
  const queue = await dbGetAll(STORES.queue);
  console.log('[App] Processing offline queue:', queue.length, 'items');
  for (const action of queue) {
    try {
      await fetch(action.url, {
        method: action.method,
        headers: action.headers,
        body: action.body || undefined,
      });
      await dbDelete(STORES.queue, action.id);
    } catch (err) {
      console.warn('[App] Failed to replay action:', action.url);
    }
  }
}

// ─── Network Status ────────────────────────────────────────────────────────────
function updateNetworkStatus(isOnline) {
  state.isOnline = isOnline;
  const dot = document.querySelector('.offline-dot');
  const statusText = document.getElementById('connectionStatus');
  const toast = document.getElementById('offlineToast');

  if (dot) dot.classList.toggle('offline', !isOnline);
  if (statusText) statusText.textContent = isOnline ? 'Online' : 'Offline';

  if (!isOnline) {
    toast?.classList.remove('hidden');
  } else {
    toast?.classList.add('hidden');
    processOfflineQueue();
  }
}

window.addEventListener('online', () => updateNetworkStatus(true));
window.addEventListener('offline', () => updateNetworkStatus(false));

// ─── Navigation Drawer ─────────────────────────────────────────────────────────
function openNavDrawer() {
  const drawer = document.getElementById('navDrawer');
  const overlay = document.getElementById('navOverlay');
  const toggle = document.getElementById('menuToggle');
  drawer?.classList.add('open');
  drawer?.removeAttribute('aria-hidden');
  overlay?.classList.add('visible');
  toggle?.setAttribute('aria-expanded', 'true');
}

function closeNavDrawer() {
  const drawer = document.getElementById('navDrawer');
  const overlay = document.getElementById('navOverlay');
  const toggle = document.getElementById('menuToggle');
  drawer?.classList.remove('open');
  drawer?.setAttribute('aria-hidden', 'true');
  overlay?.classList.remove('visible');
  toggle?.setAttribute('aria-expanded', 'false');
}

// ─── UI Helpers ────────────────────────────────────────────────────────────────
function showToast(message, duration = 3000) {
  let toast = document.getElementById('offlineToast');
  // Create dynamic toast if needed
  const t = document.createElement('div');
  t.className = 'toast';
  t.textContent = message;
  t.setAttribute('role', 'alert');
  document.body.appendChild(t);
  setTimeout(() => t.remove(), duration);
}

function hideElement(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('hidden');
}

function showUpdateBanner() {
  const banner = document.getElementById('updateBanner');
  banner?.classList.remove('hidden');
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function viewCase(id) {
  // Navigate to case detail (would expand in production)
  console.log('[App] View case:', id);
}

// ─── Event Listeners ───────────────────────────────────────────────────────────
function setupEventListeners() {
  // Tab navigation
  document.querySelectorAll('.tab-btn, .nav-item[data-view]').forEach((el) => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      const view = el.dataset.view;
      if (view) navigateTo(view);
    });
  });

  // Menu toggle
  document.getElementById('menuToggle')?.addEventListener('click', openNavDrawer);
  document.getElementById('closeNav')?.addEventListener('click', closeNavDrawer);
  document.getElementById('navOverlay')?.addEventListener('click', closeNavDrawer);

  // Install buttons
  document.getElementById('installBtn')?.addEventListener('click', triggerInstall);
  document.getElementById('installAccept')?.addEventListener('click', triggerInstall);
  document.getElementById('installDismiss')?.addEventListener('click', () => hideElement('installBanner'));

  // Notification toggle
  document.getElementById('notifToggle')?.addEventListener('change', (e) => {
    if (e.target.checked) requestNotificationPermission();
    else { showToast('🔕 Notifications disabled'); }
  });

  // Clear cache
  document.getElementById('clearCacheBtn')?.addEventListener('click', async () => {
    navigator.serviceWorker?.controller?.postMessage({ type: 'CLEAR_CACHE' });
    showToast('🗑️ Cache cleared');
  });

  // Update button
  document.getElementById('updateBtn')?.addEventListener('click', () => {
    navigator.serviceWorker?.controller?.postMessage({ type: 'SKIP_WAITING' });
    window.location.reload();
  });

  // Sync button
  document.getElementById('syncBtn')?.addEventListener('click', async () => {
    const btn = document.getElementById('syncBtn');
    if (btn) btn.textContent = '⟳';
    await loadViewData(state.currentView);
    if (btn) btn.textContent = '⟳';
    showToast('✅ Synced');
  });

  // Quick actions
  document.querySelectorAll('.action-btn[data-action]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const action = btn.dataset.action;
      if (action === 'research') navigateTo('research');
      else if (action === 'deadline') navigateTo('deadlines');
      else if (action === 'new-case') navigateTo('cases');
      else if (action === 'run-agent') navigateTo('agents');
    });
  });

  // Filter chips
  document.querySelectorAll('.filter-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('.filter-chip').forEach((c) => c.classList.remove('active'));
      chip.classList.add('active');
    });
  });

  // Research search
  document.getElementById('searchBtn')?.addEventListener('click', runResearch);

  // Hash routing
  window.addEventListener('popstate', (e) => {
    if (e.state?.view) navigateTo(e.state.view);
  });

  // SW cache size message
  navigator.serviceWorker?.addEventListener('message', (e) => {
    if (e.data?.type === 'CACHE_SIZE') {
      const el = document.getElementById('cacheSize');
      if (el) el.textContent = `${e.data.size} cached items`;
    }
  });
}

async function runResearch() {
  const query = document.getElementById('researchQuery')?.value.trim();
  if (!query) return;
  const resultsPanel = document.getElementById('researchResults');
  if (!resultsPanel) return;
  resultsPanel.innerHTML = '<div class="loading-state">🔍 Searching...</div>';
  try {
    const data = await apiPost('/research/query', { query });
    if (data?.results) {
      resultsPanel.innerHTML = data.results.map((r) => `
        <div class="card" style="margin-top:12px">
          <strong>${escapeHtml(r.title)}</strong>
          <p style="font-size:13px;color:var(--text-secondary);margin-top:8px">${escapeHtml(r.summary)}</p>
          <div style="font-size:12px;color:var(--text-muted);margin-top:6px">${escapeHtml(r.citation || '')}</div>
        </div>
      `).join('');
    }
  } catch {
    resultsPanel.innerHTML = '<div class="loading-state">❌ Search failed. Check your connection.</div>';
  }
}

// ─── Init ──────────────────────────────────────────────────────────────────────
async function init() {
  console.log('[App] SintraPrime PWA initializing...');
  try {
    await initDB();
    await registerServiceWorker();
    setupEventListeners();
    updateNetworkStatus(navigator.onLine);

    // Load initial view from hash or default
    const hash = window.location.hash.replace('#', '') || 'dashboard';
    navigateTo(hash);

    console.log('[App] SintraPrime PWA ready');
  } catch (err) {
    console.error('[App] Init failed:', err);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
