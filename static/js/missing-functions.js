// Missing JavaScript functions that are referenced in template onclick handlers
// These functions were missing and causing JavaScript errors

// Camera capture functionality
function initCameraCapture(inputId, title = 'Capture Photo') {
    console.log('initCameraCapture called for:', inputId);

    // Try multiple strategies to find the input field
    let input = null;
    let searchMethod = '';

    // Strategy 1: Find by ID
    input = document.getElementById(inputId);
    if (input) {
        searchMethod = 'by ID';
    }

    // Strategy 2: Find by name attribute
    if (!input) {
        input = document.querySelector(`input[name="${inputId}"]`);
        if (input) {
            searchMethod = 'by name attribute';
        }
    }

    // Strategy 3: Find by name attribute with variations
    if (!input) {
        const variations = [`${inputId}_file`, `${inputId}_input`, inputId.replace('_photo', '')];
        for (const variation of variations) {
            input = document.querySelector(`input[name="${variation}"]`);
            if (input) {
                searchMethod = `by name variation "${variation}"`;
                break;
            }
        }
    }

    // Strategy 4: Find in the same container as the button clicked
    if (!input) {
        const clickedButton = event?.target;
        if (clickedButton) {
            const container = clickedButton.closest('.card-body, .form-group, .mb-3, .col-md-4');
            if (container) {
                input = container.querySelector('input[type="file"]');
                if (input) {
                    searchMethod = 'in button container';
                }
            }
        }
    }

    // Strategy 5: For duty photos, create temporary input if needed
    if (!input && (inputId === 'start_photo' || inputId === 'end_photo')) {
        input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.capture = 'camera';
        input.style.display = 'none';
        input.id = inputId;
        input.name = inputId;
        document.body.appendChild(input);
        searchMethod = 'created temporary camera input';
    }

    // Strategy 6: Find any visible image input as fallback
    if (!input) {
        const imageInputs = document.querySelectorAll('input[type="file"][accept*="image"]:not([style*="display: none"])');
        if (imageInputs.length > 0) {
            input = imageInputs[0];
            searchMethod = 'first visible image input (fallback)';
        }
    }

    if (!input) {
        console.error('Input element not found after all search strategies for:', inputId);
        console.log('Available file inputs:', document.querySelectorAll('input[type="file"]'));
        showAlert('Photo input field not found. Please use the file upload option below instead.', 'info');
        return;
    }

    console.log(`Found input ${searchMethod}:`, input);

    // Check if browser supports getUserMedia
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showAlert('Camera not supported on this device', 'warning');
        // Fallback to regular file input
        input.click();
        return;
    }

    // Trigger the file input (which should trigger camera on mobile)
    input.setAttribute('capture', 'camera');
    input.click();
}

// CSV Export functionality
function exportToCSV() {
    console.log('exportToCSV called');

    try {
        // Find the main data table on the page
        const table = document.querySelector('table.table');
        if (!table) {
            showAlert('No data table found to export', 'warning');
            return;
        }

        // Get table headers
        const headers = [];
        const headerRows = table.querySelectorAll('thead th');
        headerRows.forEach(th => {
            headers.push(th.textContent.trim());
        });

        // Get table rows
        const rows = [];
        const dataRows = table.querySelectorAll('tbody tr');
        dataRows.forEach(tr => {
            const row = [];
            const cells = tr.querySelectorAll('td');
            cells.forEach(td => {
                // Clean up cell content (remove HTML tags)
                let cellText = td.textContent.trim();
                // Handle commas in data by wrapping in quotes
                if (cellText.includes(',')) {
                    cellText = `"${cellText}"`;
                }
                row.push(cellText);
            });
            if (row.length > 0) {
                rows.push(row);
            }
        });

        // Create CSV content
        let csvContent = '';
        if (headers.length > 0) {
            csvContent += headers.join(',') + '\n';
        }
        rows.forEach(row => {
            csvContent += row.join(',') + '\n';
        });

        // Download CSV
        if (csvContent) {
            downloadCSV(csvContent, 'report_export.csv');
            showAlert('Report exported successfully', 'success');
        } else {
            showAlert('No data available to export', 'warning');
        }

    } catch (error) {
        console.error('Export error:', error);
        showAlert('Failed to export data', 'danger');
    }
}

function downloadCSV(csvContent, filename) {
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');

    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    } else {
        showAlert('CSV download not supported on this browser', 'warning');
    }
}

// Calendar functionality for scheduling
function refreshCalendar() {
    console.log('refreshCalendar called');

    try {
        const calendarContainer = document.querySelector('.calendar-container, .schedule-calendar, #calendar');
        if (!calendarContainer) {
            console.error('Calendar container not found');
            showAlert('Calendar not found', 'warning');
            return;
        }

        // Show loading state
        const originalContent = calendarContainer.innerHTML;
        calendarContainer.innerHTML = '<div class="text-center p-4"><i class="fas fa-spinner fa-spin"></i> Refreshing calendar...</div>';

        // Reload the page to refresh calendar data
        setTimeout(() => {
            window.location.reload();
        }, 1000);

    } catch (error) {
        console.error('Calendar refresh error:', error);
        showAlert('Failed to refresh calendar', 'danger');
    }
}

// Week navigation functions
let currentWeekOffset = 0;

function previousWeek() {
    console.log('previousWeek called');

    try {
        currentWeekOffset--;
        updateWeekDisplay();

        // If there's a form or data to update, trigger it
        const weekForm = document.querySelector('form[data-week-form]');
        if (weekForm) {
            const weekInput = weekForm.querySelector('input[name="week_offset"]');
            if (weekInput) {
                weekInput.value = currentWeekOffset;
                weekForm.submit();
                return;
            }
        }

        // Otherwise, reload with week parameter
        const url = new URL(window.location);
        url.searchParams.set('week_offset', currentWeekOffset);
        window.location.href = url.toString();

    } catch (error) {
        console.error('Previous week error:', error);
        showAlert('Failed to navigate to previous week', 'danger');
    }
}

function nextWeek() {
    console.log('nextWeek called');

    try {
        currentWeekOffset++;
        updateWeekDisplay();

        // If there's a form or data to update, trigger it
        const weekForm = document.querySelector('form[data-week-form]');
        if (weekForm) {
            const weekInput = weekForm.querySelector('input[name="week_offset"]');
            if (weekInput) {
                weekInput.value = currentWeekOffset;
                weekForm.submit();
                return;
            }
        }

        // Otherwise, reload with week parameter
        const url = new URL(window.location);
        url.searchParams.set('week_offset', currentWeekOffset);
        window.location.href = url.toString();

    } catch (error) {
        console.error('Next week error:', error);
        showAlert('Failed to navigate to next week', 'danger');
    }
}

function updateWeekDisplay() {
    const weekDisplay = document.querySelector('.week-display, .current-week');
    if (!weekDisplay) return;

    const today = new Date();
    const weekStart = new Date(today);
    weekStart.setDate(today.getDate() + (currentWeekOffset * 7));

    const options = { month: 'short', day: 'numeric' };
    const startStr = weekStart.toLocaleDateString('en-US', options);

    const weekEnd = new Date(weekStart);
    weekEnd.setDate(weekStart.getDate() + 6);
    const endStr = weekEnd.toLocaleDateString('en-US', options);

    weekDisplay.textContent = `${startStr} - ${endStr}`;
}

// Quick assignment submission
function submitQuickAssignment() {
    console.log('submitQuickAssignment called');

    try {
        const form = document.querySelector('form[data-quick-assignment]');
        if (!form) {
            console.error('Quick assignment form not found');
            showAlert('Assignment form not found', 'warning');
            return;
        }

        // Validate required fields
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;

        requiredFields.forEach(field => {
            if (!field.value || !field.value.trim()) {
                field.classList.add('is-invalid');
                isValid = false;
            } else {
                field.classList.remove('is-invalid');
                field.classList.add('is-valid');
            }
        });

        if (!isValid) {
            showAlert('Please fill in all required fields', 'warning');
            return;
        }

        // Show loading state
        const submitBtn = form.querySelector('button[type="submit"], button[onclick*="submitQuickAssignment"]');
        if (submitBtn) {
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';

            // Reset button after timeout
            setTimeout(() => {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }, 10000);
        }

        // Submit the form
        form.submit();

    } catch (error) {
        console.error('Quick assignment error:', error);
        showAlert('Failed to create assignment', 'danger');
    }
}

// Utility function for showing alerts (reuse from dashboard.js or create if not available)
function showAlert(message, type = 'info', duration = 5000) {
    // Check if dashboard showNotification function exists
    if (typeof window.dashboardUtils !== 'undefined' && window.dashboardUtils.showNotification) {
        window.dashboardUtils.showNotification(message, type, duration);
        return;
    }

    // Fallback alert implementation
    console.log(`${type.toUpperCase()}: ${message}`);

    // Try to show Bootstrap alert
    try {
        let alertContainer = document.querySelector('.alert-container');
        if (!alertContainer) {
            alertContainer = document.createElement('div');
            alertContainer.className = 'alert-container position-fixed top-0 end-0 p-3';
            alertContainer.style.zIndex = '9999';
            document.body.appendChild(alertContainer);
        }

        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.setAttribute('role', 'alert');
        // Use safe DOM methods to prevent XSS
        alertDiv.textContent = message;

        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'btn-close';
        closeButton.setAttribute('data-bs-dismiss', 'alert');
        closeButton.setAttribute('aria-label', 'Close');

        alertDiv.appendChild(closeButton);

        alertContainer.appendChild(alertDiv);

        // Auto-dismiss after duration
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.classList.remove('show');
                setTimeout(() => {
                    if (alertDiv.parentNode) {
                        alertDiv.parentNode.removeChild(alertDiv);
                    }
                }, 150);
            }
        }, duration);

    } catch (error) {
        // Ultimate fallback
        alert(`${type.toUpperCase()}: ${message}`);
    }
}

// Get CSRF token from meta tag or form
function getCSRFToken() {
    // Try to get from meta tag first
    const metaToken = document.querySelector('meta[name=csrf-token]');
    if (metaToken) {
        return metaToken.getAttribute('content');
    }

    // Try to get from hidden form field
    const hiddenToken = document.querySelector('input[name=csrf_token]');
    if (hiddenToken) {
        return hiddenToken.value;
    }

    // Try to get from any form
    const formToken = document.querySelector('form input[name=csrf_token]');
    if (formToken) {
        return formToken.value;
    }

    return null;
}

// Add CSRF token to all AJAX requests
function setupCSRFForAjax() {
    const token = getCSRFToken();
    if (token) {
        // Setup for jQuery if available
        if (typeof $ !== 'undefined' && $.ajaxSetup) {
            $.ajaxSetup({
                beforeSend: function(xhr, settings) {
                    if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                        xhr.setRequestHeader("X-CSRFToken", token);
                    }
                }
            });
        }

        // Setup for fetch API with improved token handling
        if (!window.originalFetch) {
            window.originalFetch = window.fetch;
        }
        
        window.fetch = function(url, options = {}) {
            // Get fresh token for each request
            const currentToken = getCSRFToken();
            
            // Only add CSRF token for non-GET requests and non-CORS requests
            if (options.method && !/^(GET|HEAD|OPTIONS|TRACE)$/i.test(options.method)) {
                options.headers = options.headers || {};
                if (currentToken) {
                    options.headers['X-CSRFToken'] = currentToken;
                }
            }
            // Also add for POST requests without explicit method
            else if (!options.method && options.body) {
                options.headers = options.headers || {};
                if (currentToken) {
                    options.headers['X-CSRFToken'] = currentToken;
                }
            }
            
            return window.originalFetch(url, options);
        };
    }
}

// Helper function to add CSRF token to FormData
function addCSRFToFormData(formData) {
    const token = getCSRFToken();
    if (token && formData instanceof FormData) {
        formData.append('csrf_token', token);
    }
    return formData;
}

// Initialize CSRF protection immediately and when DOM is ready
setupCSRFForAjax();

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupCSRFForAjax);
} else {
    setupCSRFForAjax();
}

// Re-setup CSRF after any dynamic content changes
if (typeof MutationObserver !== 'undefined') {
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                // Check if new forms were added
                for (let node of mutation.addedNodes) {
                    if (node.nodeType === 1 && (node.tagName === 'FORM' || node.querySelector('form'))) {
                        setupCSRFForAjax();
                        break;
                    }
                }
            }
        });
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
}

// Performance monitoring for slow page loads
(function() {
    const startTime = performance.now();

    window.addEventListener('load', function() {
        const loadTime = performance.now() - startTime;
        if (loadTime > 5000) { // Log if page takes more than 5 seconds
            console.warn('Slow page load detected:', loadTime + 'ms');

            // Optional: Send performance data to server
            if (typeof fetch !== 'undefined') {
                fetch('/api/performance-log', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken()
                    },
                    body: JSON.stringify({
                        loadTime: loadTime,
                        url: window.location.href,
                        userAgent: navigator.userAgent
                    })
                }).catch(function(error) {
                    // Silently fail - don't disrupt user experience
                });
            }
        }
    });
})();

// Initialize any week display on page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize current week offset from URL if present
    const urlParams = new URLSearchParams(window.location.search);
    const weekOffset = urlParams.get('week_offset');
    if (weekOffset) {
        currentWeekOffset = parseInt(weekOffset) || 0;
    }

    updateWeekDisplay();
    console.log('Missing functions script loaded successfully');
});