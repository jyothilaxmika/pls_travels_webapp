// PWA Installation and App-like Navigation Enhancement
class PWAInstallManager {
  constructor() {
    this.deferredPrompt = null;
    this.isInstalled = false;
    this.isStandalone = false;
    
    this.init();
  }
  
  init() {
    this.checkInstallStatus();
    this.setupEventListeners();
    this.enhanceNavigation();
    this.setupInstallBanner();
  }
  
  checkInstallStatus() {
    // Check if app is running in standalone mode
    this.isStandalone = window.matchMedia('(display-mode: standalone)').matches ||
                      window.navigator.standalone ||
                      document.referrer.includes('android-app://');
    
    // Check if app is already installed
    this.isInstalled = this.isStandalone;
    
    if (this.isInstalled) {
      console.log('[PWA-Install] App is running in installed mode');
      this.enhanceInstalledExperience();
    }
  }
  
  setupEventListeners() {
    // Listen for beforeinstallprompt event
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      this.deferredPrompt = e;
      console.log('[PWA-Install] Install prompt available');
      
      if (!this.isInstalled) {
        this.showInstallBanner();
      }
    });
    
    // Listen for appinstalled event
    window.addEventListener('appinstalled', () => {
      console.log('[PWA-Install] App was installed');
      this.deferredPrompt = null;
      this.isInstalled = true;
      this.hideInstallBanner();
      this.showSuccessMessage();
      this.enhanceInstalledExperience();
    });
    
    // Listen for display mode changes
    window.matchMedia('(display-mode: standalone)').addEventListener('change', (e) => {
      this.isStandalone = e.matches;
      if (this.isStandalone) {
        this.enhanceInstalledExperience();
      }
    });
  }
  
  enhanceNavigation() {
    // Add swipe gestures for mobile navigation
    if ('ontouchstart' in window) {
      this.setupSwipeNavigation();
    }
    
    // Add keyboard shortcuts
    this.setupKeyboardShortcuts();
    
    // Enhance back button behavior
    this.enhanceBackButton();
  }
  
  setupSwipeNavigation() {
    let startX = null;
    let startY = null;
    
    document.addEventListener('touchstart', (e) => {
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
    });
    
    document.addEventListener('touchend', (e) => {
      if (!startX || !startY) return;
      
      const endX = e.changedTouches[0].clientX;
      const endY = e.changedTouches[0].clientY;
      
      const diffX = startX - endX;
      const diffY = startY - endY;
      
      // Swipe threshold
      const threshold = 100;
      
      if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > threshold) {
        if (diffX > 0) {
          // Swipe left - go forward
          this.handleSwipeLeft();
        } else {
          // Swipe right - go back
          this.handleSwipeRight();
        }
      }
      
      startX = null;
      startY = null;
    });
  }
  
  handleSwipeLeft() {
    // Implement forward navigation logic
    console.log('[PWA-Install] Swipe left detected');
  }
  
  handleSwipeRight() {
    // Implement back navigation logic
    if (window.history.length > 1) {
      window.history.back();
    }
  }
  
  setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      // Alt + H - Home
      if (e.altKey && e.key === 'h') {
        e.preventDefault();
        window.location.href = '/';
      }
      
      // Alt + D - Dashboard
      if (e.altKey && e.key === 'd') {
        e.preventDefault();
        if (window.location.pathname.includes('/admin/')) {
          window.location.href = '/admin/dashboard';
        } else if (window.location.pathname.includes('/driver/')) {
          window.location.href = '/driver/dashboard';
        }
      }
      
      // Ctrl + K - Quick search (future enhancement)
      if (e.ctrlKey && e.key === 'k') {
        e.preventDefault();
        this.openQuickSearch();
      }
    });
  }
  
  enhanceBackButton() {
    // Add visual feedback for back navigation
    const backButtons = document.querySelectorAll('[data-action="back"]');
    backButtons.forEach(button => {
      button.addEventListener('click', (e) => {
        e.preventDefault();
        window.history.back();
      });
    });
  }
  
  setupInstallBanner() {
    // Create persistent install banner for eligible devices
    if (!this.isInstalled && this.shouldShowInstallPrompt()) {
      setTimeout(() => {
        this.showInstallBanner();
      }, 5000); // Show after 5 seconds
    }
  }
  
  shouldShowInstallPrompt() {
    // Check if user has previously dismissed install prompt
    const dismissed = localStorage.getItem('pwa-install-dismissed');
    if (dismissed) {
      const dismissedTime = new Date(dismissed);
      const now = new Date();
      const daysSinceDismissed = (now - dismissedTime) / (1000 * 60 * 60 * 24);
      
      // Show again after 7 days
      return daysSinceDismissed >= 7;
    }
    
    return true;
  }
  
  showInstallBanner() {
    // Don't show if already showing or installed
    if (document.getElementById('pwa-install-banner') || this.isInstalled) {
      return;
    }
    
    const banner = document.createElement('div');
    banner.id = 'pwa-install-banner';
    banner.className = 'pwa-install-banner';
    banner.innerHTML = `
      <div class="pwa-banner-content">
        <div class="pwa-banner-icon">
          <i class="fas fa-mobile-alt"></i>
        </div>
        <div class="pwa-banner-text">
          <div class="pwa-banner-title">Install PLS TRAVELS</div>
          <div class="pwa-banner-subtitle">Get quick access and work offline</div>
        </div>
        <div class="pwa-banner-actions">
          <button class="pwa-btn-install" onclick="pwaInstall.installApp()">
            <i class="fas fa-download me-1"></i>Install
          </button>
          <button class="pwa-btn-close" onclick="pwaInstall.dismissBanner()">
            <i class="fas fa-times"></i>
          </button>
        </div>
      </div>
    `;
    
    document.body.appendChild(banner);
    
    // Add styles
    this.addInstallBannerStyles();
    
    // Animate in
    setTimeout(() => {
      banner.classList.add('show');
    }, 100);
  }
  
  addInstallBannerStyles() {
    const styles = `
      .pwa-install-banner {
        position: fixed;
        bottom: -100px;
        left: 20px;
        right: 20px;
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        border-radius: 12px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
        z-index: 1060;
        transition: bottom 0.3s ease-in-out;
        max-width: 400px;
        margin: 0 auto;
      }
      
      .pwa-install-banner.show {
        bottom: 20px;
      }
      
      .pwa-banner-content {
        display: flex;
        align-items: center;
        padding: 16px;
        gap: 12px;
      }
      
      .pwa-banner-icon {
        font-size: 24px;
        opacity: 0.9;
      }
      
      .pwa-banner-text {
        flex: 1;
      }
      
      .pwa-banner-title {
        font-weight: 600;
        font-size: 16px;
        margin-bottom: 2px;
      }
      
      .pwa-banner-subtitle {
        font-size: 13px;
        opacity: 0.8;
      }
      
      .pwa-banner-actions {
        display: flex;
        gap: 8px;
      }
      
      .pwa-btn-install {
        background: rgba(255, 255, 255, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.3);
        color: white;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: 500;
        font-size: 14px;
        cursor: pointer;
        transition: all 0.2s ease;
      }
      
      .pwa-btn-install:hover {
        background: rgba(255, 255, 255, 0.3);
        transform: translateY(-1px);
      }
      
      .pwa-btn-close {
        background: transparent;
        border: none;
        color: white;
        padding: 8px;
        border-radius: 4px;
        cursor: pointer;
        opacity: 0.7;
        transition: opacity 0.2s ease;
      }
      
      .pwa-btn-close:hover {
        opacity: 1;
      }
      
      @media (max-width: 768px) {
        .pwa-install-banner {
          left: 10px;
          right: 10px;
        }
        
        .pwa-banner-content {
          padding: 12px;
        }
        
        .pwa-banner-title {
          font-size: 15px;
        }
        
        .pwa-banner-subtitle {
          font-size: 12px;
        }
      }
    `;
    
    const styleElement = document.createElement('style');
    styleElement.textContent = styles;
    document.head.appendChild(styleElement);
  }
  
  hideInstallBanner() {
    const banner = document.getElementById('pwa-install-banner');
    if (banner) {
      banner.classList.remove('show');
      setTimeout(() => {
        banner.remove();
      }, 300);
    }
  }
  
  dismissBanner() {
    this.hideInstallBanner();
    localStorage.setItem('pwa-install-dismissed', new Date().toISOString());
  }
  
  async installApp() {
    if (!this.deferredPrompt) {
      this.showFallbackInstallInstructions();
      return;
    }
    
    try {
      this.deferredPrompt.prompt();
      const result = await this.deferredPrompt.userChoice;
      
      console.log('[PWA-Install] User choice:', result.outcome);
      
      if (result.outcome === 'accepted') {
        this.hideInstallBanner();
      }
      
      this.deferredPrompt = null;
    } catch (error) {
      console.error('[PWA-Install] Install failed:', error);
      this.showFallbackInstallInstructions();
    }
  }
  
  showFallbackInstallInstructions() {
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    const isAndroid = /Android/.test(navigator.userAgent);
    
    let instructions = '';
    
    if (isIOS) {
      instructions = `
        <div class="install-instructions">
          <h5><i class="fab fa-apple me-2"></i>Install on iOS</h5>
          <ol>
            <li>Tap the Share button <i class="fas fa-share"></i></li>
            <li>Scroll down and tap "Add to Home Screen"</li>
            <li>Tap "Add" to install PLS TRAVELS</li>
          </ol>
        </div>
      `;
    } else if (isAndroid) {
      instructions = `
        <div class="install-instructions">
          <h5><i class="fab fa-android me-2"></i>Install on Android</h5>
          <ol>
            <li>Tap the menu button <i class="fas fa-ellipsis-v"></i></li>
            <li>Select "Add to Home screen" or "Install app"</li>
            <li>Confirm to install PLS TRAVELS</li>
          </ol>
        </div>
      `;
    } else {
      instructions = `
        <div class="install-instructions">
          <h5><i class="fas fa-desktop me-2"></i>Install on Desktop</h5>
          <ol>
            <li>Look for the install icon in your browser's address bar</li>
            <li>Or check your browser's menu for "Install PLS TRAVELS"</li>
            <li>Follow the prompts to install</li>
          </ol>
        </div>
      `;
    }
    
    this.showModal('Install PLS TRAVELS App', instructions);
  }
  
  showModal(title, content) {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.innerHTML = `
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">${title}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            ${content}
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
          </div>
        </div>
      </div>
    `;
    
    document.body.appendChild(modal);
    
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
    
    modal.addEventListener('hidden.bs.modal', () => {
      modal.remove();
    });
  }
  
  enhanceInstalledExperience() {
    // Add app-like behaviors for installed version
    this.hideAddressBar();
    this.preventZoom();
    this.enhanceStatusBar();
    this.addAppBadging();
  }
  
  hideAddressBar() {
    // Auto-hide address bar on mobile
    if (window.innerHeight < window.innerWidth) return;
    
    setTimeout(() => {
      window.scrollTo(0, 1);
    }, 0);
  }
  
  preventZoom() {
    // Prevent pinch zoom in installed app
    document.addEventListener('gesturestart', (e) => {
      e.preventDefault();
    });
    
    document.addEventListener('gesturechange', (e) => {
      e.preventDefault();
    });
    
    document.addEventListener('gestureend', (e) => {
      e.preventDefault();
    });
  }
  
  enhanceStatusBar() {
    // Update status bar color based on page
    const updateStatusBar = () => {
      const isDarkPage = document.body.classList.contains('dark-theme');
      const metaThemeColor = document.querySelector('meta[name="theme-color"]');
      
      if (metaThemeColor) {
        metaThemeColor.content = isDarkPage ? '#1a1a1a' : '#1e3a8a';
      }
    };
    
    updateStatusBar();
    
    // Watch for theme changes
    const observer = new MutationObserver(updateStatusBar);
    observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });
  }
  
  addAppBadging() {
    // Add app badge for notifications (if supported)
    if ('setAppBadge' in navigator) {
      this.setupAppBadging();
    }
  }
  
  setupAppBadging() {
    // Example: Update app badge based on notifications
    const updateBadge = (count) => {
      if (count > 0) {
        navigator.setAppBadge(count);
      } else {
        navigator.clearAppBadge();
      }
    };
    
    // Listen for notification updates
    window.addEventListener('notifications-updated', (e) => {
      updateBadge(e.detail.count);
    });
  }
  
  openQuickSearch() {
    // Placeholder for quick search functionality
    console.log('[PWA-Install] Quick search opened');
    // TODO: Implement quick search modal
  }
  
  showSuccessMessage() {
    const toast = document.createElement('div');
    toast.className = 'toast align-items-center text-white bg-success border-0 position-fixed';
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 1070;';
    toast.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">
          <i class="fas fa-check-circle me-2"></i>
          PLS TRAVELS installed successfully!
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
      </div>
    `;
    
    document.body.appendChild(toast);
    
    const bootstrapToast = new bootstrap.Toast(toast);
    bootstrapToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
      toast.remove();
    });
  }
}

// Initialize PWA Install Manager
let pwaInstall;

document.addEventListener('DOMContentLoaded', () => {
  pwaInstall = new PWAInstallManager();
  window.pwaInstall = pwaInstall;
  console.log('[PWA-Install] PWA Install Manager ready');
});

// Add helper functions for enhanced navigation
window.PWANavigation = {
  goBack: () => {
    if (window.history.length > 1) {
      window.history.back();
    } else {
      window.location.href = '/';
    }
  },
  
  goHome: () => {
    window.location.href = '/';
  },
  
  goDashboard: () => {
    if (window.location.pathname.includes('/admin/')) {
      window.location.href = '/admin/dashboard';
    } else if (window.location.pathname.includes('/driver/')) {
      window.location.href = '/driver/dashboard';
    } else {
      window.location.href = '/';
    }
  },
  
  refresh: () => {
    window.location.reload();
  }
};