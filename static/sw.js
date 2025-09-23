// PLS TRAVELS Service Worker - PWA Implementation
const CACHE_NAME = 'pls-travels-v1.0.0';
const STATIC_CACHE = 'pls-travels-static-v1';
const DYNAMIC_CACHE = 'pls-travels-dynamic-v1';

// Core app shell files to cache
const CORE_FILES = [
  '/',
  '/auth/login',
  '/driver/dashboard',
  '/admin/dashboard',
  '/static/css/custom.css',
  '/static/css/driver-mobile.css',
  '/static/css/responsive-enhancements.css',
  '/static/js/dashboard.js',
  '/static/js/duty.js',
  '/static/js/missing-functions.js',
  '/static/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png'
];

// URLs that should always be fetched from network
const NETWORK_FIRST = [
  '/api/',
  '/admin/api/',
  '/driver/api/',
  '/auth/',
  '/admin/manual-earnings',
  '/admin/duties',
  '/driver/duties'
];

// URLs for offline fallback
const OFFLINE_FALLBACK = '/offline.html';

// Install event - cache core files
self.addEventListener('install', event => {
  console.log('[SW] Installing service worker');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('[SW] Caching core files');
        return cache.addAll(CORE_FILES);
      })
      .then(() => {
        console.log('[SW] Core files cached successfully');
        return self.skipWaiting();
      })
      .catch(err => {
        console.error('[SW] Failed to cache core files:', err);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('[SW] Activating service worker');
  
  event.waitUntil(
    Promise.all([
      // Clean up old caches
      caches.keys().then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => {
            if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
              console.log('[SW] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      }),
      // Take control of all pages
      self.clients.claim()
    ])
  );
});

// Fetch event - implement caching strategies
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }
  
  // Skip Chrome extensions
  if (url.protocol === 'chrome-extension:') {
    return;
  }
  
  // Network first for API calls and critical data
  if (NETWORK_FIRST.some(pattern => url.pathname.startsWith(pattern))) {
    event.respondWith(networkFirst(event.request));
    return;
  }
  
  // Cache first for static assets
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(cacheFirst(event.request));
    return;
  }
  
  // Stale while revalidate for pages
  event.respondWith(staleWhileRevalidate(event.request));
});

// Background sync for offline actions
self.addEventListener('sync', event => {
  console.log('[SW] Background sync triggered:', event.tag);
  
  if (event.tag === 'duty-sync') {
    event.waitUntil(syncDutyData());
  } else if (event.tag === 'photo-upload') {
    event.waitUntil(syncPhotoUploads());
  } else if (event.tag === 'earnings-sync') {
    event.waitUntil(syncEarningsData());
  }
});

// Push notification handling
self.addEventListener('push', event => {
  console.log('[SW] Push notification received');
  
  let notificationData = {
    title: 'PLS TRAVELS',
    body: 'You have a new notification',
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/icon-72x72.png',
    tag: 'pls-travels-notification',
    data: {}
  };
  
  if (event.data) {
    try {
      const payload = event.data.json();
      notificationData = { ...notificationData, ...payload };
    } catch (e) {
      notificationData.body = event.data.text();
    }
  }
  
  event.waitUntil(
    self.registration.showNotification(notificationData.title, {
      body: notificationData.body,
      icon: notificationData.icon,
      badge: notificationData.badge,
      tag: notificationData.tag,
      data: notificationData.data,
      actions: [
        {
          action: 'view',
          title: 'View',
          icon: '/static/icons/action-view.png'
        },
        {
          action: 'dismiss',
          title: 'Dismiss',
          icon: '/static/icons/action-dismiss.png'
        }
      ],
      requireInteraction: notificationData.requireInteraction || false,
      silent: false,
      vibrate: [200, 100, 200]
    })
  );
});

// Notification click handling
self.addEventListener('notificationclick', event => {
  console.log('[SW] Notification clicked:', event.action);
  
  event.notification.close();
  
  if (event.action === 'view') {
    const urlToOpen = event.notification.data.url || '/';
    event.waitUntil(
      clients.matchAll({ type: 'window' }).then(windowClients => {
        // Check if there's already a window/tab open with the target URL
        for (let client of windowClients) {
          if (client.url === urlToOpen && 'focus' in client) {
            return client.focus();
          }
        }
        // If not, open a new window/tab
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen);
        }
      })
    );
  }
});

// Caching strategies
async function networkFirst(request) {
  try {
    const response = await fetch(request);
    
    if (response.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, response.clone());
    }
    
    return response;
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', request.url);
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Return offline fallback for navigation requests
    if (request.mode === 'navigate') {
      return caches.match(OFFLINE_FALLBACK);
    }
    
    throw error;
  }
}

async function cacheFirst(request) {
  const cachedResponse = await caches.match(request);
  
  if (cachedResponse) {
    return cachedResponse;
  }
  
  try {
    const response = await fetch(request);
    
    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, response.clone());
    }
    
    return response;
  } catch (error) {
    console.error('[SW] Cache first failed:', error);
    throw error;
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(DYNAMIC_CACHE);
  const cachedResponse = await cache.match(request);
  
  const fetchPromise = fetch(request).then(response => {
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  }).catch(error => {
    console.log('[SW] Fetch failed:', error);
    return cachedResponse;
  });
  
  return cachedResponse || fetchPromise;
}

// Background sync functions
async function syncDutyData() {
  console.log('[SW] Syncing duty data');
  
  try {
    // Get offline duty data from IndexedDB
    const offlineDuties = await getOfflineData('duties');
    
    for (const duty of offlineDuties) {
      try {
        const response = await fetch('/api/duties/sync', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(duty)
        });
        
        if (response.ok) {
          await removeOfflineData('duties', duty.id);
          console.log('[SW] Duty synced successfully:', duty.id);
        }
      } catch (error) {
        console.error('[SW] Failed to sync duty:', duty.id, error);
      }
    }
  } catch (error) {
    console.error('[SW] Duty sync failed:', error);
  }
}

async function syncPhotoUploads() {
  console.log('[SW] Syncing photo uploads');
  
  try {
    const offlinePhotos = await getOfflineData('photos');
    
    for (const photo of offlinePhotos) {
      try {
        const formData = new FormData();
        formData.append('photo', photo.blob, photo.filename);
        formData.append('duty_id', photo.duty_id);
        formData.append('photo_type', photo.photo_type);
        
        const response = await fetch('/api/photos/upload', {
          method: 'POST',
          body: formData
        });
        
        if (response.ok) {
          await removeOfflineData('photos', photo.id);
          console.log('[SW] Photo synced successfully:', photo.id);
        }
      } catch (error) {
        console.error('[SW] Failed to sync photo:', photo.id, error);
      }
    }
  } catch (error) {
    console.error('[SW] Photo sync failed:', error);
  }
}

async function syncEarningsData() {
  console.log('[SW] Syncing earnings data');
  
  try {
    const offlineEarnings = await getOfflineData('earnings');
    
    for (const earning of offlineEarnings) {
      try {
        const response = await fetch('/api/earnings/sync', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(earning)
        });
        
        if (response.ok) {
          await removeOfflineData('earnings', earning.id);
          console.log('[SW] Earnings synced successfully:', earning.id);
        }
      } catch (error) {
        console.error('[SW] Failed to sync earnings:', earning.id, error);
      }
    }
  } catch (error) {
    console.error('[SW] Earnings sync failed:', error);
  }
}

// IndexedDB helper functions
async function getOfflineData(storeName) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('PLSTravelsDB', 1);
    
    request.onsuccess = event => {
      const db = event.target.result;
      const transaction = db.transaction([storeName], 'readonly');
      const store = transaction.objectStore(storeName);
      const getRequest = store.getAll();
      
      getRequest.onsuccess = () => resolve(getRequest.result);
      getRequest.onerror = () => reject(getRequest.error);
    };
    
    request.onerror = () => reject(request.error);
  });
}

async function removeOfflineData(storeName, id) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('PLSTravelsDB', 1);
    
    request.onsuccess = event => {
      const db = event.target.result;
      const transaction = db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      const deleteRequest = store.delete(id);
      
      deleteRequest.onsuccess = () => resolve();
      deleteRequest.onerror = () => reject(deleteRequest.error);
    };
    
    request.onerror = () => reject(request.error);
  });
}