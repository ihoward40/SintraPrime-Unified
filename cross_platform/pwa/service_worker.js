/**
 * SintraPrime Service Worker
 * Implements cache-first for static assets, network-first for API calls.
 * Handles offline gracefully with fallback pages.
 */

const CACHE_VERSION = 'v1.0.0';
const STATIC_CACHE = `sintra-static-${CACHE_VERSION}`;
const API_CACHE = `sintra-api-${CACHE_VERSION}`;
const IMAGE_CACHE = `sintra-images-${CACHE_VERSION}`;

const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/app.js',
  '/styles.css',
  '/manifest.json',
  '/offline.html',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
];

const API_ROUTES = [
  '/api/cases',
  '/api/deadlines',
  '/api/research',
  '/api/health',
  '/api/documents',
];

const CACHE_DURATION_API = 5 * 60 * 1000; // 5 minutes for API responses
const CACHE_DURATION_IMAGES = 7 * 24 * 60 * 60 * 1000; // 7 days for images

// ─── Install ──────────────────────────────────────────────────────────────────
self.addEventListener('install', (event) => {
  console.log('[SW] Installing SintraPrime Service Worker', CACHE_VERSION);
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      console.log('[SW] Pre-caching static assets');
      return cache.addAll(STATIC_ASSETS);
    }).then(() => {
      console.log('[SW] Static assets cached successfully');
      return self.skipWaiting();
    }).catch((err) => {
      console.warn('[SW] Pre-cache failed (some assets may be missing):', err);
      return self.skipWaiting();
    })
  );
});

// ─── Activate ─────────────────────────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating new service worker');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => {
            return (
              name.startsWith('sintra-') &&
              ![STATIC_CACHE, API_CACHE, IMAGE_CACHE].includes(name)
            );
          })
          .map((name) => {
            console.log('[SW] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    }).then(() => self.clients.claim())
  );
});

// ─── Fetch Strategy ───────────────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests for caching (but allow background sync to handle them)
  if (request.method !== 'GET') {
    event.respondWith(handleMutation(request));
    return;
  }

  // API routes: network-first with cache fallback
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirstStrategy(request, API_CACHE));
    return;
  }

  // Images: cache-first with long TTL
  if (request.destination === 'image') {
    event.respondWith(cacheFirstStrategy(request, IMAGE_CACHE));
    return;
  }

  // Static assets: cache-first
  event.respondWith(cacheFirstStrategy(request, STATIC_CACHE));
});

// ─── Cache Strategies ─────────────────────────────────────────────────────────

async function networkFirstStrategy(request, cacheName) {
  try {
    const networkResponse = await fetch(request.clone());
    if (networkResponse && networkResponse.status === 200) {
      const cache = await caches.open(cacheName);
      const responseToCache = networkResponse.clone();
      // Add timestamp header for expiry checking
      const headers = new Headers(responseToCache.headers);
      headers.append('sw-fetched-at', Date.now().toString());
      cache.put(request, new Response(await responseToCache.text(), {
        status: responseToCache.status,
        statusText: responseToCache.statusText,
        headers: headers,
      }));
    }
    return networkResponse;
  } catch (err) {
    console.warn('[SW] Network failed, falling back to cache:', request.url);
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    // Return offline JSON for API calls
    if (request.url.includes('/api/')) {
      return new Response(
        JSON.stringify({ error: 'offline', message: 'You are currently offline. Data may be stale.' }),
        { status: 503, headers: { 'Content-Type': 'application/json' } }
      );
    }
    return caches.match('/offline.html');
  }
}

async function cacheFirstStrategy(request, cacheName) {
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    // Refresh cache in background
    refreshCacheInBackground(request, cacheName);
    return cachedResponse;
  }
  try {
    const networkResponse = await fetch(request);
    if (networkResponse && networkResponse.status === 200) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (err) {
    console.warn('[SW] Failed to fetch:', request.url);
    if (request.destination === 'document') {
      return caches.match('/offline.html');
    }
    return new Response('', { status: 404 });
  }
}

function refreshCacheInBackground(request, cacheName) {
  fetch(request.clone()).then((response) => {
    if (response && response.status === 200) {
      caches.open(cacheName).then((cache) => cache.put(request, response));
    }
  }).catch(() => {/* silent fail */});
}

async function handleMutation(request) {
  try {
    return await fetch(request);
  } catch (err) {
    // Queue for background sync
    if ('SyncManager' in self) {
      await queueOfflineAction(request);
      return new Response(
        JSON.stringify({ queued: true, message: 'Action queued for when you come back online' }),
        { status: 202, headers: { 'Content-Type': 'application/json' } }
      );
    }
    return new Response(
      JSON.stringify({ error: 'offline', message: 'Cannot perform this action while offline' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

async function queueOfflineAction(request) {
  const body = await request.text().catch(() => '');
  const action = {
    url: request.url,
    method: request.method,
    headers: Object.fromEntries(request.headers.entries()),
    body,
    timestamp: Date.now(),
  };
  // Store in IndexedDB via message to main thread
  self.clients.matchAll().then((clients) => {
    clients.forEach((client) => {
      client.postMessage({ type: 'QUEUE_OFFLINE_ACTION', action });
    });
  });
}

// ─── Background Sync ──────────────────────────────────────────────────────────
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync triggered:', event.tag);
  if (event.tag === 'sintra-offline-queue') {
    event.waitUntil(processOfflineQueue());
  } else if (event.tag === 'sintra-deadline-check') {
    event.waitUntil(checkDeadlines());
  }
});

async function processOfflineQueue() {
  // Notify clients to process their queued actions
  const clients = await self.clients.matchAll();
  clients.forEach((client) => {
    client.postMessage({ type: 'PROCESS_OFFLINE_QUEUE' });
  });
}

async function checkDeadlines() {
  try {
    const response = await fetch('/api/deadlines/upcoming?days=7');
    if (response.ok) {
      const data = await response.json();
      if (data.deadlines && data.deadlines.length > 0) {
        self.registration.showNotification('SintraPrime: Upcoming Deadlines', {
          body: `You have ${data.deadlines.length} deadline(s) in the next 7 days`,
          icon: '/icons/icon-192x192.png',
          badge: '/icons/icon-72x72.png',
          tag: 'deadline-reminder',
          requireInteraction: true,
          data: { url: '/deadlines' },
        });
      }
    }
  } catch (err) {
    console.warn('[SW] Failed to check deadlines:', err);
  }
}

// ─── Push Notifications ───────────────────────────────────────────────────────
self.addEventListener('push', (event) => {
  console.log('[SW] Push notification received');
  if (!event.data) return;

  let data;
  try {
    data = event.data.json();
  } catch {
    data = { title: 'SintraPrime', body: event.data.text(), type: 'general' };
  }

  const options = buildNotificationOptions(data);
  event.waitUntil(
    self.registration.showNotification(data.title || 'SintraPrime', options)
  );
});

function buildNotificationOptions(data) {
  const base = {
    icon: '/icons/icon-192x192.png',
    badge: '/icons/icon-72x72.png',
    vibrate: [200, 100, 200],
    data: { url: data.url || '/', type: data.type },
    actions: [],
    timestamp: Date.now(),
  };

  switch (data.type) {
    case 'court_deadline':
      return {
        ...base,
        body: data.body || 'Court deadline approaching',
        tag: 'court-deadline',
        requireInteraction: true,
        actions: [
          { action: 'view', title: '📋 View Case' },
          { action: 'dismiss', title: 'Dismiss' },
        ],
      };
    case 'case_law_update':
      return {
        ...base,
        body: data.body || 'New relevant case law found',
        tag: 'case-law-update',
        actions: [
          { action: 'view', title: '⚖️ Read Now' },
          { action: 'later', title: 'Later' },
        ],
      };
    case 'document_ready':
      return {
        ...base,
        body: data.body || 'Document is ready for signature',
        tag: 'document-ready',
        requireInteraction: true,
        actions: [
          { action: 'sign', title: '✍️ Sign Now' },
          { action: 'view', title: 'View' },
        ],
      };
    case 'agent_completed':
      return {
        ...base,
        body: data.body || 'AI agent task completed',
        tag: 'agent-task',
        actions: [
          { action: 'view', title: '🤖 View Results' },
        ],
      };
    case 'emergency':
      return {
        ...base,
        body: data.body || 'Time-sensitive legal matter requires attention',
        tag: 'emergency',
        requireInteraction: true,
        vibrate: [500, 100, 500, 100, 500],
        actions: [
          { action: 'view', title: '🚨 View Now' },
        ],
      };
    default:
      return { ...base, body: data.body || 'New notification from SintraPrime' };
  }
}

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const { action } = event;
  const { url, type } = event.notification.data || {};

  let targetUrl = url || '/';

  if (action === 'sign') targetUrl = '/documents/sign';
  else if (action === 'later') return;
  else if (action === 'dismiss') return;

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      // Focus existing window if open
      for (const client of clients) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.navigate(targetUrl);
          return client.focus();
        }
      }
      // Open new window
      return self.clients.openWindow(targetUrl);
    })
  );
});

// ─── Message Handling ─────────────────────────────────────────────────────────
self.addEventListener('message', (event) => {
  const { type, data } = event.data || {};

  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;
    case 'CACHE_URLS':
      event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => cache.addAll(data.urls || []))
      );
      break;
    case 'CLEAR_CACHE':
      event.waitUntil(
        caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k))))
      );
      break;
    case 'GET_CACHE_SIZE':
      event.waitUntil(getCacheSize().then((size) => {
        event.source.postMessage({ type: 'CACHE_SIZE', size });
      }));
      break;
  }
});

async function getCacheSize() {
  const keys = await caches.keys();
  let total = 0;
  for (const key of keys) {
    const cache = await caches.open(key);
    const requests = await cache.keys();
    total += requests.length;
  }
  return total;
}

console.log('[SW] SintraPrime Service Worker loaded:', CACHE_VERSION);
