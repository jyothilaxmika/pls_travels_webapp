// PLS TRAVELS PWA Installation and Management
// Version 1.0 - Production Ready

class PLSTravelsPWA {
  constructor() {
    this.deferredPrompt = null;
    this.isInstalled = false;
    this.swRegistration = null;
    
    this.init();
  }

  async init() {
    console.log('Initializing PLS TRAVELS PWA...');
    
    // Register service worker
    await this.registerServiceWorker();
    
    // Setup install prompt
    this.setupInstallPrompt();
    
    // Check if already installed
    this.checkInstallStatus();
    
    // Setup push notifications
    this.setupPushNotifications();
    
    // Add iOS specific meta tags
    this.addIOSMetaTags();
  }

  async registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        this.swRegistration = await navigator.serviceWorker.register('/static/sw.js', {
          scope: '/'
        });
        
        console.log('Service Worker registered successfully:', this.swRegistration);
        
        // Listen for updates
        this.swRegistration.addEventListener('updatefound', () => {
          const newWorker = this.swRegistration.installing;
          
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              this.showUpdateAvailable();
            }
          });
        });
        
      } catch (error) {
        console.error('Service Worker registration failed:', error);
      }
    }
  }

  setupInstallPrompt() {
    // Listen for the beforeinstallprompt event
    window.addEventListener('beforeinstallprompt', (event) => {
      console.log('PWA install prompt available');
      
      // Prevent the mini-infobar from appearing on mobile
      event.preventDefault();
      
      // Stash the event so it can be triggered later
      this.deferredPrompt = event;
      
      // Show install button
      this.showInstallButton();
    });

    // Listen for successful installation
    window.addEventListener('appinstalled', (event) => {
      console.log('PWA installed successfully');
      this.isInstalled = true;
      this.hideInstallButton();
      this.showInstallSuccess();
    });
  }

  showInstallButton() {
    // Create install button if it doesn't exist
    let installBtn = document.getElementById('pwa-install-btn');
    
    if (!installBtn) {
      installBtn = document.createElement('button');
      installBtn.id = 'pwa-install-btn';
      installBtn.className = 'btn btn-primary position-fixed';
      installBtn.style.cssText = `
        bottom: 20px;
        right: 20px;
        z-index: 1050;
        border-radius: 50px;
        padding: 15px 25px;
        box-shadow: 0 4px 20px rgba(0, 212, 255, 0.4);
        font-weight: 600;
      `;
      installBtn.innerHTML = '<i class="fas fa-download me-2"></i>Install App';
      
      installBtn.addEventListener('click', () => this.installPWA());
      
      document.body.appendChild(installBtn);
    }
    
    installBtn.style.display = 'block';
  }

  hideInstallButton() {
    const installBtn = document.getElementById('pwa-install-btn');
    if (installBtn) {
      installBtn.style.display = 'none';
    }
  }

  async installPWA() {
    if (!this.deferredPrompt) {
      return;
    }

    // Show the install prompt
    this.deferredPrompt.prompt();

    // Wait for the user to respond
    const { outcome } = await this.deferredPrompt.userChoice;
    
    console.log('PWA install prompt outcome:', outcome);
    
    if (outcome === 'accepted') {
      console.log('User accepted the install prompt');
    } else {
      console.log('User dismissed the install prompt');
    }

    // Clear the deferredPrompt
    this.deferredPrompt = null;
    this.hideInstallButton();
  }

  checkInstallStatus() {
    // Check if running in standalone mode (installed)
    if (window.matchMedia('(display-mode: standalone)').matches || 
        window.navigator.standalone === true) {
      this.isInstalled = true;
      console.log('PWA is running in standalone mode');
      this.hideInstallButton();
    }
  }

  async setupPushNotifications() {
    if ('Notification' in window && 'serviceWorker' in navigator) {
      // Check current permission status
      if (Notification.permission === 'default') {
        this.showNotificationPrompt();
      } else if (Notification.permission === 'granted') {
        await this.subscribeToPushNotifications();
      }
    }
  }

  showNotificationPrompt() {
    // Create notification prompt
    const notificationBar = document.createElement('div');
    notificationBar.id = 'notification-prompt';
    notificationBar.className = 'alert alert-info alert-dismissible fade show position-fixed';
    notificationBar.style.cssText = `
      top: 20px;
      left: 20px;
      right: 20px;
      z-index: 1060;
      border-radius: 10px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
    `;
    
    notificationBar.innerHTML = `
      <div class="d-flex align-items-center">
        <i class="fas fa-bell me-3"></i>
        <div class="flex-grow-1">
          <strong>Stay Updated!</strong><br>
          <small>Enable notifications for duty updates and important alerts</small>
        </div>
        <button type="button" class="btn btn-sm btn-primary me-2" onclick="plsPWA.requestNotificationPermission()">
          Enable
        </button>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      </div>
    `;
    
    document.body.appendChild(notificationBar);
    
    // Auto-hide after 10 seconds
    setTimeout(() => {
      if (notificationBar.parentNode) {
        notificationBar.remove();
      }
    }, 10000);
  }

  async requestNotificationPermission() {
    const permission = await Notification.requestPermission();
    
    if (permission === 'granted') {
      console.log('Notification permission granted');
      await this.subscribeToPushNotifications();
      
      // Hide notification prompt
      const prompt = document.getElementById('notification-prompt');
      if (prompt) {
        prompt.remove();
      }
      
      // Show success message
      this.showNotificationSuccess();
    }
  }

  async subscribeToPushNotifications() {
    if (this.swRegistration) {
      try {
        const subscription = await this.swRegistration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: this.urlBase64ToUint8Array(
            'BEl62iUYgUivxIkv69yViEuiBIa40HI80YWlh0KNdN4RwjbMvGWwFR5M5LWqWLmbJrxrmRKdLFb0jLQnZ8dXPNs'
          )
        });

        console.log('Push subscription created:', subscription);
        
        // Send subscription to server
        await this.sendSubscriptionToServer(subscription);
        
      } catch (error) {
        console.error('Failed to subscribe to push notifications:', error);
      }
    }
  }

  async sendSubscriptionToServer(subscription) {
    try {
      const response = await fetch('/api/mobile/v1/push/subscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(subscription)
      });
      
      if (response.ok) {
        console.log('Push subscription sent to server successfully');
      }
    } catch (error) {
      console.error('Failed to send subscription to server:', error);
    }
  }

  urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/-/g, '+')
      .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  addIOSMetaTags() {
    // Add iOS-specific meta tags for better PWA support
    const metaTags = [
      { name: 'apple-mobile-web-app-capable', content: 'yes' },
      { name: 'apple-mobile-web-app-status-bar-style', content: 'black-translucent' },
      { name: 'apple-mobile-web-app-title', content: 'PLS TRAVELS' },
      { name: 'apple-touch-fullscreen', content: 'yes' }
    ];

    metaTags.forEach(tag => {
      if (!document.querySelector(`meta[name="${tag.name}"]`)) {
        const meta = document.createElement('meta');
        meta.name = tag.name;
        meta.content = tag.content;
        document.head.appendChild(meta);
      }
    });

    // Add iOS app icons
    const iconSizes = [57, 60, 72, 76, 114, 120, 144, 152, 180];
    iconSizes.forEach(size => {
      const link = document.createElement('link');
      link.rel = 'apple-touch-icon';
      link.sizes = `${size}x${size}`;
      link.href = `/static/icons/icon-${size}x${size}.png`;
      document.head.appendChild(link);
    });
  }

  showInstallSuccess() {
    this.showToast('Success!', 'PLS TRAVELS app installed successfully', 'success');
  }

  showNotificationSuccess() {
    this.showToast('Notifications Enabled!', 'You\'ll receive important updates', 'success');
  }

  showUpdateAvailable() {
    this.showToast('Update Available!', 'A new version is ready. Refresh to update.', 'info', 0);
  }

  showToast(title, message, type = 'info', duration = 5000) {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('pwa-toast-container');
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.id = 'pwa-toast-container';
      toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
      toastContainer.style.zIndex = '1070';
      document.body.appendChild(toastContainer);
    }

    // Create toast
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : type === 'info' ? 'info' : 'primary'} border-0`;
    toast.setAttribute('role', 'alert');
    
    toast.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">
          <strong>${title}</strong><br>
          ${message}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
      </div>
    `;

    toastContainer.appendChild(toast);

    // Show toast
    const bsToast = new bootstrap.Toast(toast, {
      autohide: duration > 0,
      delay: duration
    });
    bsToast.show();

    // Remove toast element after hiding
    toast.addEventListener('hidden.bs.toast', () => {
      toast.remove();
    });
  }

  // Utility method to check if online
  isOnline() {
    return navigator.onLine;
  }

  // Method to manually trigger sync
  async triggerSync() {
    if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
      const registration = await navigator.serviceWorker.ready;
      await registration.sync.register('duty-sync');
      console.log('Background sync triggered');
    }
  }
}

// Initialize PWA when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  window.plsPWA = new PLSTravelsPWA();
});

// Handle online/offline status
window.addEventListener('online', () => {
  console.log('App is online');
  if (window.plsPWA) {
    window.plsPWA.showToast('Online', 'Connection restored', 'success');
  }
});

window.addEventListener('offline', () => {
  console.log('App is offline');
  if (window.plsPWA) {
    window.plsPWA.showToast('Offline', 'Working in offline mode', 'warning');
  }
});

console.log('PLS TRAVELS PWA scripts loaded successfully');