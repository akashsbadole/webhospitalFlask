// Enterprise Hospital Management System - Service Worker
const CACHE_NAME = 'medicare-pro-v2.0';
const STATIC_CACHE = 'medicare-static-v2.0';
const DYNAMIC_CACHE = 'medicare-dynamic-v2.0';

// Critical resources to cache immediately
const STATIC_ASSETS = [
  '/',
  '/static/style.css',
  '/login',
  '/dashboard',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap',
  'https://unpkg.com/htmx.org@1.9.10',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
  'https://code.jquery.com/jquery-3.6.0.min.js',
  'https://cdn.jsdelivr.net/npm/sweetalert2@11'
];

// Dynamic content patterns
const DYNAMIC_PATTERNS = [
  /\/patients/,
  /\/appointments/,
  /\/api\//,
  /\/dashboard/
];

// Install event - cache static assets
self.addEventListener('install', event => {
  console.log('[SW] Installing Service Worker...');
  
  event.waitUntil(
    Promise.all([
      caches.open(STATIC_CACHE).then(cache => {
        console.log('[SW] Caching static assets...');
        return cache.addAll(STATIC_ASSETS);
      }),
      caches.open(DYNAMIC_CACHE).then(cache => {
        console.log('[SW] Dynamic cache initialized...');
        return cache;
      })
    ])
  );
  
  // Force activation of new service worker
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('[SW] Activating Service Worker...');
  
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  
  // Take control of all clients immediately
  self.clients.claim();
});

// Fetch event - implement caching strategies
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Handle different types of requests
  if (isStaticAsset(request)) {
    event.respondWith(cacheFirst(request));
  } else if (isDynamicContent(request)) {
    event.respondWith(networkFirst(request));
  } else if (isAPIRequest(request)) {
    event.respondWith(networkOnly(request));
  } else {
    event.respondWith(staleWhileRevalidate(request));
  }
});

// Cache strategies
async function cacheFirst(request) {
  try {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log('[SW] Cache first failed:', error);
    return new Response('Offline - Resource not available', { status: 503 });
  }
}

async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network first fallback to cache:', error);
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    return createOfflinePage();
  }
}

async function networkOnly(request) {
  try {
    return await fetch(request);
  } catch (error) {
    console.log('[SW] Network only failed:', error);
    return new Response(JSON.stringify({
      error: 'Network unavailable',
      offline: true,
      timestamp: new Date().toISOString()
    }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(DYNAMIC_CACHE);
  const cachedResponse = await cache.match(request);
  
  const fetchPromise = fetch(request).then(networkResponse => {
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  }).catch(() => cachedResponse);
  
  return cachedResponse || fetchPromise;
}

// Helper functions
function isStaticAsset(request) {
  return request.url.includes('/static/') || 
         request.url.includes('bootstrap') ||
         request.url.includes('font-awesome') ||
         request.url.includes('fonts.googleapis') ||
         request.url.includes('jquery') ||
         request.url.includes('sweetalert');
}

function isDynamicContent(request) {
  return DYNAMIC_PATTERNS.some(pattern => pattern.test(request.url));
}

function isAPIRequest(request) {
  return request.url.includes('/api/');
}

function createOfflinePage() {
  return new Response(`
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Offline - MediCare Pro</title>
        <style>
            body {
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                color: #374151;
            }
            .offline-container {
                text-align: center;
                padding: 2rem;
                background: white;
                border-radius: 16px;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
                max-width: 400px;
            }
            .offline-icon {
                font-size: 4rem;
                color: #ef4444;
                margin-bottom: 1rem;
            }
            .offline-title {
                font-size: 1.5rem;
                font-weight: 700;
                margin-bottom: 1rem;
                color: #1f2937;
            }
            .offline-message {
                color: #6b7280;
                margin-bottom: 2rem;
                line-height: 1.6;
            }
            .retry-btn {
                background: linear-gradient(135deg, #3b82f6, #2563eb);
                color: white;
                border: none;
                padding: 0.75rem 1.5rem;
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
            }
            .retry-btn:hover {
                transform: translateY(-2px);
            }
        </style>
    </head>
    <body>
        <div class="offline-container">
            <div class="offline-icon">📡</div>
            <h1 class="offline-title">You're Offline</h1>
            <p class="offline-message">
                It looks like you've lost your internet connection. 
                Please check your connection and try again.
            </p>
            <button class="retry-btn" onclick="window.location.reload()">
                Try Again
            </button>
        </div>
    </body>
    </html>
  `, {
    headers: { 'Content-Type': 'text/html' }
  });
}

// Background sync for offline data
self.addEventListener('sync', event => {
  console.log('[SW] Background sync triggered:', event.tag);
  
  if (event.tag === 'patient-data-sync') {
    event.waitUntil(syncPatientData());
  } else if (event.tag === 'appointment-sync') {
    event.waitUntil(syncAppointmentData());
  } else if (event.tag === 'general-sync') {
    event.waitUntil(syncOfflineData());
  }
});

async function syncPatientData() {
  try {
    const offlineData = await getOfflineData('patients');
    if (offlineData.length > 0) {
      const response = await fetch('/api/sync-offline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'patients',
          data: offlineData,
          timestamp: new Date().toISOString()
        })
      });
      
      if (response.ok) {
        await clearOfflineData('patients');
        console.log('[SW] Patient data synced successfully');
      }
    }
  } catch (error) {
    console.error('[SW] Patient data sync failed:', error);
  }
}

async function syncAppointmentData() {
  try {
    const offlineData = await getOfflineData('appointments');
    if (offlineData.length > 0) {
      const response = await fetch('/api/sync-offline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'appointments',
          data: offlineData,
          timestamp: new Date().toISOString()
        })
      });
      
      if (response.ok) {
        await clearOfflineData('appointments');
        console.log('[SW] Appointment data synced successfully');
      }
    }
  } catch (error) {
    console.error('[SW] Appointment data sync failed:', error);
  }
}

async function syncOfflineData() {
  try {
    const allOfflineData = await getAllOfflineData();
    if (Object.keys(allOfflineData).length > 0) {
      const response = await fetch('/api/sync-offline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'all',
          data: allOfflineData,
          timestamp: new Date().toISOString()
        })
      });
      
      if (response.ok) {
        await clearAllOfflineData();
        console.log('[SW] All offline data synced successfully');
      }
    }
  } catch (error) {
    console.error('[SW] General data sync failed:', error);
  }
}

// IndexedDB operations for offline data storage
async function getOfflineData(type) {
  // Implementation would use IndexedDB to retrieve offline data
  return [];
}

async function getAllOfflineData() {
  // Implementation would use IndexedDB to retrieve all offline data
  return {};
}

async function clearOfflineData(type) {
  // Implementation would use IndexedDB to clear specific offline data
  console.log(`[SW] Cleared offline data for: ${type}`);
}

async function clearAllOfflineData() {
  // Implementation would use IndexedDB to clear all offline data
  console.log('[SW] Cleared all offline data');
}

// Push notification handling
self.addEventListener('push', event => {
  console.log('[SW] Push notification received');
  
  const options = {
    body: event.data ? event.data.text() : 'New notification from MediCare Pro',
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/badge-72x72.png',
    vibrate: [200, 100, 200],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'View Details',
        icon: '/static/icons/checkmark.png'
      },
      {
        action: 'close',
        title: 'Close',
        icon: '/static/icons/xmark.png'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification('MediCare Pro', options)
  );
});

// Notification click handling
self.addEventListener('notificationclick', event => {
  console.log('[SW] Notification clicked');
  
  event.notification.close();
  
  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/dashboard')
    );
  }
});

// Message handling from main thread
self.addEventListener('message', event => {
  console.log('[SW] Message received:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

console.log('[SW] Service Worker loaded successfully');