// Dashboard JavaScript functionality for PLS TRAVELS

// Initialize dashboard on load
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});

function initializeDashboard() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Initialize real-time updates
    initializeRealTimeUpdates();
}

// Real-time updates for dashboard metrics
function initializeRealTimeUpdates() {
    // Update time displays every minute
    setInterval(updateTimeDisplays, 60000);
    
    // Auto-refresh dashboard data every 5 minutes for active users
    if (isUserActive()) {
        setInterval(refreshDashboardData, 300000); // 5 minutes
    }
}

function updateTimeDisplays() {
    var timeElements = document.querySelectorAll('.current-time');
    var now = new Date();
    var timeString = now.toLocaleTimeString('en-IN', { 
        hour12: true, 
        hour: '2-digit', 
        minute: '2-digit' 
    });
    
    timeElements.forEach(function(element) {
        element.textContent = timeString;
    });
}

function isUserActive() {
    // Check if user is on an active dashboard page
    var dashboardPages = ['/admin/dashboard', '/manager/dashboard', '/driver/dashboard'];
    return dashboardPages.some(page => window.location.pathname.includes(page));
}

function refreshDashboardData() {
    // Only refresh if user is still active on the page
    if (document.hidden) return;
    
    // Reload page for fresh data
    if (isUserActive()) {
        window.location.reload();
    }
}

// Chart utility functions
function createChart(canvasId, chartConfig) {
    var ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    
    return new Chart(ctx.getContext('2d'), chartConfig);
}

function getChartColors() {
    return {
        primary: 'rgba(13, 110, 253, 0.8)',
        success: 'rgba(25, 135, 84, 0.8)',
        warning: 'rgba(255, 193, 7, 0.8)',
        danger: 'rgba(220, 53, 69, 0.8)',
        info: 'rgba(13, 202, 240, 0.8)',
        secondary: 'rgba(108, 117, 125, 0.8)'
    };
}

// Number formatting utilities
function formatCurrency(amount) {
    return '₹' + amount.toLocaleString('en-IN', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    });
}

function formatNumber(number) {
    return number.toLocaleString('en-IN');
}

// Progress bar animations
function animateProgressBars() {
    var progressBars = document.querySelectorAll('.progress-bar');
    
    progressBars.forEach(function(bar) {
        var width = bar.getAttribute('aria-valuenow');
        if (width) {
            bar.style.width = '0%';
            setTimeout(function() {
                bar.style.transition = 'width 1s ease-in-out';
                bar.style.width = width + '%';
            }, 100);
        }
    });
}

// Initialize progress bar animations on page load
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(animateProgressBars, 500);
});

// Mobile-specific functionality
function isMobile() {
    return window.innerWidth <= 768;
}

function optimizeForMobile() {
    if (isMobile()) {
        // Collapse cards that are not essential on mobile
        var collapsibleCards = document.querySelectorAll('.card-collapsible');
        collapsibleCards.forEach(function(card) {
            var cardBody = card.querySelector('.card-body');
            if (cardBody) {
                cardBody.classList.add('collapse');
            }
        });
        
        // Make tables more mobile-friendly
        var tables = document.querySelectorAll('.table-responsive table');
        tables.forEach(function(table) {
            table.classList.add('table-sm');
        });
    }
}

// Call mobile optimization on load and resize
document.addEventListener('DOMContentLoaded', optimizeForMobile);
window.addEventListener('resize', optimizeForMobile);

// Form validation helpers
function validateForm(formId) {
    var form = document.getElementById(formId);
    if (!form) return false;
    
    var isValid = true;
    var requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(function(field) {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
        }
    });
    
    return isValid;
}

// Loading state management
function showLoading(elementId) {
    var element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '<div class="text-center py-3"><i class="fas fa-spinner fa-spin fa-2x"></i><br>Loading...</div>';
    }
}

function hideLoading(elementId, content) {
    var element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = content;
    }
}

// Notification system
function showNotification(message, type = 'info', duration = 5000) {
    var alertContainer = document.getElementById('alert-container');
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.id = 'alert-container';
        alertContainer.style.position = 'fixed';
        alertContainer.style.top = '20px';
        alertContainer.style.right = '20px';
        alertContainer.style.zIndex = '9999';
        document.body.appendChild(alertContainer);
    }
    
    var alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertContainer.appendChild(alertDiv);
    
    // Auto-dismiss after duration
    setTimeout(function() {
        if (alertDiv.parentNode) {
            alertDiv.classList.remove('show');
            setTimeout(function() {
                if (alertDiv.parentNode) {
                    alertDiv.parentNode.removeChild(alertDiv);
                }
            }, 150);
        }
    }, duration);
}

// Data refresh utilities
function refreshCardData(cardId, url) {
    var card = document.querySelector(`#${cardId} .card-body`);
    if (!card) return;
    
    showLoading(cardId + '-body');
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            updateCardContent(cardId, data);
        })
        .catch(error => {
            console.error('Error refreshing data:', error);
            showNotification('Failed to refresh data', 'danger');
        });
}

function updateCardContent(cardId, data) {
    // This would be implemented based on specific card types
    // and data structures for each dashboard
    console.log('Updating card:', cardId, 'with data:', data);
}

// Export functions for global use
window.dashboardUtils = {
    formatCurrency,
    formatNumber,
    showNotification,
    validateForm,
    showLoading,
    hideLoading,
    refreshCardData,
    createChart,
    getChartColors,
    isMobile
};

// Error handling
window.addEventListener('error', function(e) {
    console.error('Dashboard error:', e.error);
    showNotification('An error occurred. Please refresh the page.', 'danger');
});

// Performance monitoring
window.addEventListener('load', function() {
    // Log page load time for performance monitoring
    var loadTime = performance.now();
    if (loadTime > 3000) {
        console.warn('Slow page load detected:', loadTime + 'ms');
    }
});
