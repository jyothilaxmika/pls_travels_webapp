// PLS TRAVELS Service Worker
// Version 1.0 - Production Ready

const CACHE_NAME = 'pls-travels-v1.1';
const OFFLINE_URL = '/offline';

// Resources to cache for offline functionality
const PRECACHE_RESOURCES = [
  '/',
  '/static/css/custom.css',
  '/static/css/responsive-enhancements.css',
  '/static/css/driver-mobile.css',
  '/static/js/dashboard.js',
  '/static/js/duty.js',
  '/static/js/missing-functions.js',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  '/offline',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'
];

// Install event - precache resources
self.addEventListener('install', (event) => {
  console.log('PLS TRAVELS Service Worker installing...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Precaching resources...');
        return cache.addAll(PRECACHE_RESOURCES);
      })
      .then(() => {
        console.log('PLS TRAVELS Service Worker installed successfully');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('Error during install:', error);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('PLS TRAVELS Service Worker activating...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== CACHE_NAME) {
              console.log('Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('PLS TRAVELS Service Worker activated');
        return self.clients.claim();
      })
  );
});

// Fetch event - serve cached content when offline
self.addEventListener('fetch', (event) => {
  // Skip non-HTTP requests
  if (!event.request.url.startsWith('http')) {
    return;
  }

  // Handle navigation requests (page loads)
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .catch(() => {
          return caches.open(CACHE_NAME)
            .then((cache) => {
              return cache.match(OFFLINE_URL);
            });
        })
    );
    return;
  }

  // Handle API requests with network-first strategy
  if (event.request.url.includes('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // Cache successful API responses
          if (response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME)
              .then((cache) => {
                cache.put(event.request, responseClone);
              });
          }
          return response;
        })
        .catch(() => {
          // Fallback to cached API response
          return caches.match(event.request)
            .then((cachedResponse) => {
              if (cachedResponse) {
                return cachedResponse;
              }
              // Return offline indicator for API calls
              return new Response(
                JSON.stringify({
                  error: 'Offline',
                  message: 'Unable to connect to PLS TRAVELS servers'
                }),
                {
                  status: 503,
                  statusText: 'Service Unavailable',
                  headers: { 'Content-Type': 'application/json' }
                }
              );
            });
        })
    );
    return;
  }

  // Handle static resources with cache-first strategy
  event.respondWith(
    caches.match(event.request)
      .then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }
        
        return fetch(event.request)
          .then((response) => {
            // Cache successful responses
            if (response.status === 200) {
              const responseClone = response.clone();
              caches.open(CACHE_NAME)
                .then((cache) => {
                  cache.put(event.request, responseClone);
                });
            }
            return response;
          })
          .catch(() => {
            // Return fallback for images
            if (event.request.destination === 'image') {
              return caches.match('/static/icons/icon-192x192.png');
            }
            throw error;
          });
      })
  );
});

// Background sync for duty updates
self.addEventListener('sync', (event) => {
  console.log('Background sync triggered:', event.tag);
  
  if (event.tag === 'duty-sync') {
    event.waitUntil(
      syncDutyData()
    );
  }
});

// Push notification handling
self.addEventListener('push', (event) => {
  console.log('Push notification received');
  
  const options = {
    body: event.data ? event.data.text() : 'New update from PLS TRAVELS',
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/icon-72x72.png',
    vibrate: [200, 100, 200],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'Open App',
        icon: '/static/icons/icon-96x96.png'
      },
      {
        action: 'close',
        title: 'Close',
        icon: '/static/icons/icon-96x96.png'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('PLS TRAVELS', options)
  );
});

// Notification click handling
self.addEventListener('notificationclick', (event) => {
  console.log('Notification clicked:', event.action);
  
  event.notification.close();

  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Sync duty data function
async function syncDutyData() {
  try {
    const response = await fetch('/api/mobile/v1/sync/duty', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    if (response.ok) {
      console.log('Duty data synced successfully');
    }
  } catch (error) {
    console.error('Failed to sync duty data:', error);
  }
}

// Periodic background sync
self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'duty-update') {
    event.waitUntil(syncDutyData());
  }
});

console.log('PLS TRAVELS Service Worker loaded successfully');