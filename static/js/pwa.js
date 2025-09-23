// PLS TRAVELS PWA Implementation
class PLSPWAManager {
  constructor() {
    this.isOnline = navigator.onLine;
    this.installPrompt = null;
    this.pushNotificationSupported = 'Notification' in window && 'serviceWorker' in navigator && 'PushManager' in window;
    this.offlineDB = null;
    
    this.init();
  }
  
  async init() {
    console.log('[PWA] Initializing PWA Manager');
    
    // Register service worker
    await this.registerServiceWorker();
    
    // Initialize offline database
    await this.initOfflineDB();
    
    // Setup event listeners
    this.setupEventListeners();
    
    // Setup camera API
    this.setupCameraAPI();
    
    // Request notification permission
    this.requestNotificationPermission();
    
    // Setup install prompt
    this.setupInstallPrompt();
    
    // Initialize background sync
    this.setupBackgroundSync();
    
    console.log('[PWA] PWA Manager initialized successfully');
  }
  
  async registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js', { scope: '/' });
        console.log('[PWA] Service Worker registered:', registration);
        
        // Handle service worker updates
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              this.showUpdateAvailable();
            }
          });
        });
        
        return registration;
      } catch (error) {
        console.error('[PWA] Service Worker registration failed:', error);
      }
    }
  }
  
  async initOfflineDB() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open('PLSTravelsDB', 1);
      
      request.onupgradeneeded = event => {
        const db = event.target.result;
        
        // Create object stores for offline data
        if (!db.objectStoreNames.contains('duties')) {
          const dutiesStore = db.createObjectStore('duties', { keyPath: 'id' });
          dutiesStore.createIndex('status', 'status', { unique: false });
          dutiesStore.createIndex('date', 'date', { unique: false });
        }
        
        if (!db.objectStoreNames.contains('photos')) {
          const photosStore = db.createObjectStore('photos', { keyPath: 'id' });
          photosStore.createIndex('duty_id', 'duty_id', { unique: false });
          photosStore.createIndex('uploaded', 'uploaded', { unique: false });
        }
        
        if (!db.objectStoreNames.contains('earnings')) {
          const earningsStore = db.createObjectStore('earnings', { keyPath: 'id' });
          earningsStore.createIndex('duty_id', 'duty_id', { unique: false });
          earningsStore.createIndex('synced', 'synced', { unique: false });
        }
        
        if (!db.objectStoreNames.contains('settings')) {
          db.createObjectStore('settings', { keyPath: 'key' });
        }
      };
      
      request.onsuccess = event => {
        this.offlineDB = event.target.result;
        console.log('[PWA] Offline database initialized');
        resolve(this.offlineDB);
      };
      
      request.onerror = event => {
        console.error('[PWA] Failed to initialize offline database:', event.target.error);
        reject(event.target.error);
      };
    });
  }
  
  setupEventListeners() {
    // Online/offline status
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.showConnectionStatus('online');
      this.syncOfflineData();
    });
    
    window.addEventListener('offline', () => {
      this.isOnline = false;
      this.showConnectionStatus('offline');
    });
    
    // Visibility change for background sync
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden && this.isOnline) {
        this.syncOfflineData();
      }
    });
  }
  
  setupCameraAPI() {
    // Enhanced camera integration
    this.cameraConstraints = {
      video: {
        facingMode: { ideal: 'environment' }, // Rear camera preferred
        width: { ideal: 1920 },
        height: { ideal: 1080 }
      }
    };
    
    console.log('[PWA] Camera API configured');
  }
  
  async requestNotificationPermission() {
    if (this.pushNotificationSupported) {
      try {
        const permission = await Notification.requestPermission();
        console.log('[PWA] Notification permission:', permission);
        
        if (permission === 'granted') {
          await this.subscribeToPushNotifications();
        }
      } catch (error) {
        console.error('[PWA] Failed to request notification permission:', error);
      }
    }
  }
  
  async subscribeToPushNotifications() {
    try {
      const registration = await navigator.serviceWorker.ready;
      
      // Check if already subscribed
      let subscription = await registration.pushManager.getSubscription();
      
      if (!subscription) {
        // Create new subscription
        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: this.urlB64ToUint8Array(await this.getVAPIDPublicKey())
        });
      }
      
      // Send subscription to server
      await this.sendSubscriptionToServer(subscription);
      
      console.log('[PWA] Push notification subscription active');
    } catch (error) {
      console.error('[PWA] Failed to subscribe to push notifications:', error);
    }
  }
  
  async getVAPIDPublicKey() {
    try {
      const response = await fetch('/api/push/vapid-key');
      const data = await response.json();
      return data.publicKey;
    } catch (error) {
      console.error('[PWA] Failed to get VAPID key:', error);
      // Fallback key for development
      return 'BMxYTchPHQqB3XHB5iUKhM8C19PGQHRwh7sW1VGo2mBBJ8eQiQh1SmxL6UO7YVHIa_TttVLTzCl9pfrEe1nxTGM';
    }
  }
  
  async sendSubscriptionToServer(subscription) {
    try {
      await fetch('/api/push/subscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          subscription: subscription.toJSON(),
          user_agent: navigator.userAgent
        })
      });
    } catch (error) {
      console.error('[PWA] Failed to send subscription to server:', error);
    }
  }
  
  setupInstallPrompt() {
    window.addEventListener('beforeinstallprompt', event => {
      event.preventDefault();
      this.installPrompt = event;
      this.showInstallPrompt();
    });
    
    window.addEventListener('appinstalled', () => {
      console.log('[PWA] App installed successfully');
      this.hideInstallPrompt();
      this.showToast('App installed successfully!', 'success');
    });
  }
  
  setupBackgroundSync() {
    if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
      console.log('[PWA] Background sync supported');
    } else {
      console.log('[PWA] Background sync not supported');
    }
  }
  
  // Camera API methods
  async openCamera(options = {}) {
    try {
      const constraints = {
        ...this.cameraConstraints,
        ...options
      };
      
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      return stream;
    } catch (error) {
      console.error('[PWA] Camera access failed:', error);
      throw new Error(`Camera access failed: ${error.message}`);
    }
  }
  
  async capturePhoto(videoElement) {
    try {
      const canvas = document.createElement('canvas');
      const context = canvas.getContext('2d');
      
      canvas.width = videoElement.videoWidth;
      canvas.height = videoElement.videoHeight;
      
      context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
      
      return new Promise(resolve => {
        canvas.toBlob(resolve, 'image/jpeg', 0.8);
      });
    } catch (error) {
      console.error('[PWA] Photo capture failed:', error);
      throw error;
    }
  }
  
  // Offline data management
  async saveOfflineData(storeName, data) {
    if (!this.offlineDB) return false;
    
    try {
      const transaction = this.offlineDB.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      await store.put(data);
      
      console.log(`[PWA] Data saved offline in ${storeName}:`, data.id);
      return true;
    } catch (error) {
      console.error(`[PWA] Failed to save offline data in ${storeName}:`, error);
      return false;
    }
  }
  
  async getOfflineData(storeName, key = null) {
    if (!this.offlineDB) return null;
    
    try {
      const transaction = this.offlineDB.transaction([storeName], 'readonly');
      const store = transaction.objectStore(storeName);
      
      if (key) {
        return await store.get(key);
      } else {
        return await store.getAll();
      }
    } catch (error) {
      console.error(`[PWA] Failed to get offline data from ${storeName}:`, error);
      return null;
    }
  }
  
  async syncOfflineData() {
    if (!this.isOnline || !('serviceWorker' in navigator)) return;
    
    try {
      const registration = await navigator.serviceWorker.ready;
      
      // Trigger background sync for different data types
      await registration.sync.register('duty-sync');
      await registration.sync.register('photo-upload');
      await registration.sync.register('earnings-sync');
      
      console.log('[PWA] Background sync registered');
    } catch (error) {
      console.error('[PWA] Background sync failed:', error);
    }
  }
  
  // Notification methods
  async showLocalNotification(title, options = {}) {
    if (!this.pushNotificationSupported) return;
    
    try {
      const notification = new Notification(title, {
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/icon-72x72.png',
        ...options
      });
      
      return notification;
    } catch (error) {
      console.error('[PWA] Failed to show notification:', error);
    }
  }
  
  // Install prompt methods
  showInstallPrompt() {
    const installBanner = document.createElement('div');
    installBanner.id = 'pwa-install-banner';
    installBanner.className = 'alert alert-info alert-dismissible fade show position-fixed';
    installBanner.style.cssText = 'top: 20px; right: 20px; z-index: 1060; max-width: 350px;';
    
    installBanner.innerHTML = `
      <div class="d-flex align-items-center">
        <i class="fas fa-mobile-alt me-2"></i>
        <div class="flex-grow-1">
          <strong>Install PLS TRAVELS</strong><br>
          <small>Add to your home screen for quick access</small>
        </div>
        <button type="button" class="btn btn-sm btn-primary ms-2" onclick="plsPWA.installApp()">
          Install
        </button>
        <button type="button" class="btn-close ms-2" data-bs-dismiss="alert"></button>
      </div>
    `;
    
    document.body.appendChild(installBanner);
  }
  
  hideInstallPrompt() {
    const banner = document.getElementById('pwa-install-banner');
    if (banner) {
      banner.remove();
    }
  }
  
  async installApp() {
    if (!this.installPrompt) return;
    
    try {
      this.installPrompt.prompt();
      const result = await this.installPrompt.userChoice;
      
      console.log('[PWA] Install prompt result:', result.outcome);
      this.installPrompt = null;
      this.hideInstallPrompt();
    } catch (error) {
      console.error('[PWA] Install failed:', error);
    }
  }
  
  // UI helpers
  showConnectionStatus(status) {
    const statusElement = document.getElementById('connection-status') || this.createConnectionStatus();
    
    if (status === 'online') {
      statusElement.className = 'alert alert-success alert-dismissible fade show position-fixed';
      statusElement.innerHTML = `
        <i class="fas fa-wifi me-2"></i>Back online - syncing data...
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      `;
      
      // Auto-hide after 3 seconds
      setTimeout(() => {
        if (statusElement.parentNode) {
          statusElement.remove();
        }
      }, 3000);
    } else {
      statusElement.className = 'alert alert-warning alert-dismissible fade show position-fixed';
      statusElement.innerHTML = `
        <i class="fas fa-wifi-slash me-2"></i>Offline mode - data will sync when online
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      `;
    }
  }
  
  createConnectionStatus() {
    const statusElement = document.createElement('div');
    statusElement.id = 'connection-status';
    statusElement.style.cssText = 'top: 20px; left: 20px; z-index: 1060; max-width: 350px;';
    document.body.appendChild(statusElement);
    return statusElement;
  }
  
  showUpdateAvailable() {
    const updateBanner = document.createElement('div');
    updateBanner.className = 'alert alert-warning alert-dismissible fade show position-fixed';
    updateBanner.style.cssText = 'bottom: 20px; right: 20px; z-index: 1060; max-width: 350px;';
    
    updateBanner.innerHTML = `
      <div class="d-flex align-items-center">
        <i class="fas fa-sync me-2"></i>
        <div class="flex-grow-1">
          <strong>Update Available</strong><br>
          <small>Refresh to get the latest version</small>
        </div>
        <button type="button" class="btn btn-sm btn-warning ms-2" onclick="window.location.reload()">
          Update
        </button>
        <button type="button" class="btn-close ms-2" data-bs-dismiss="alert"></button>
      </div>
    `;
    
    document.body.appendChild(updateBanner);
  }
  
  showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    toast.style.cssText = 'top: 20px; left: 50%; transform: translateX(-50%); z-index: 1060;';
    
    toast.innerHTML = `
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
      if (toast.parentNode) {
        toast.remove();
      }
    }, 5000);
  }
  
  // Utility methods
  urlB64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    
    return outputArray;
  }
  
  // Public API methods
  async uploadPhotoOffline(file, dutyId, photoType) {
    const photoData = {
      id: Date.now().toString(),
      blob: file,
      filename: file.name,
      duty_id: dutyId,
      photo_type: photoType,
      uploaded: false,
      timestamp: new Date().toISOString()
    };
    
    const saved = await this.saveOfflineData('photos', photoData);
    
    if (saved) {
      this.showToast('Photo saved offline - will upload when online', 'warning');
      
      if (this.isOnline) {
        this.syncOfflineData();
      }
    }
    
    return saved;
  }
  
  async saveDutyOffline(dutyData) {
    const saved = await this.saveOfflineData('duties', {
      ...dutyData,
      synced: false,
      timestamp: new Date().toISOString()
    });
    
    if (saved) {
      this.showToast('Duty data saved offline - will sync when online', 'warning');
      
      if (this.isOnline) {
        this.syncOfflineData();
      }
    }
    
    return saved;
  }
}

// Initialize PWA Manager when DOM is loaded
let plsPWA;

document.addEventListener('DOMContentLoaded', () => {
  plsPWA = new PLSPWAManager();
  
  // Make PWA manager globally available
  window.plsPWA = plsPWA;
  
  console.log('[PWA] PWA Manager ready');
});

// Enhanced camera widget for better photo capture
class CameraWidget {
  constructor(container, options = {}) {
    this.container = container;
    this.options = {
      facingMode: 'environment',
      width: 1920,
      height: 1080,
      ...options
    };
    this.stream = null;
    this.video = null;
    
    this.init();
  }
  
  async init() {
    this.createUI();
    await this.startCamera();
  }
  
  createUI() {
    this.container.innerHTML = `
      <div class="camera-widget">
        <video id="camera-video" autoplay playsinline class="w-100 rounded"></video>
        <div class="camera-controls mt-3 text-center">
          <button id="capture-btn" class="btn btn-primary btn-lg me-2">
            <i class="fas fa-camera me-2"></i>Capture
          </button>
          <button id="switch-camera-btn" class="btn btn-secondary">
            <i class="fas fa-sync-alt me-2"></i>Switch
          </button>
        </div>
        <canvas id="capture-canvas" style="display: none;"></canvas>
      </div>
    `;
    
    this.video = this.container.querySelector('#camera-video');
    this.canvas = this.container.querySelector('#capture-canvas');
    
    this.container.querySelector('#capture-btn').addEventListener('click', () => this.capture());
    this.container.querySelector('#switch-camera-btn').addEventListener('click', () => this.switchCamera());
  }
  
  async startCamera() {
    try {
      if (this.stream) {
        this.stream.getTracks().forEach(track => track.stop());
      }
      
      this.stream = await plsPWA.openCamera({
        video: {
          facingMode: { ideal: this.options.facingMode },
          width: { ideal: this.options.width },
          height: { ideal: this.options.height }
        }
      });
      
      this.video.srcObject = this.stream;
    } catch (error) {
      console.error('[Camera] Failed to start camera:', error);
      plsPWA.showToast('Camera access failed: ' + error.message, 'error');
    }
  }
  
  async capture() {
    try {
      const blob = await plsPWA.capturePhoto(this.video);
      
      if (this.options.onCapture) {
        this.options.onCapture(blob);
      }
      
      return blob;
    } catch (error) {
      console.error('[Camera] Capture failed:', error);
      plsPWA.showToast('Photo capture failed', 'error');
    }
  }
  
  async switchCamera() {
    this.options.facingMode = this.options.facingMode === 'environment' ? 'user' : 'environment';
    await this.startCamera();
  }
  
  destroy() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
    }
  }
}

// Make CameraWidget globally available
window.CameraWidget = CameraWidget;