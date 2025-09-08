// Missing JavaScript functions that are referenced in template onclick handlers
// These functions were missing and causing JavaScript errors

// Camera capture functionality
function initCameraCapture(inputId, title = 'Capture Photo') {
    console.log('initCameraCapture called for:', inputId);
    
    const input = document.getElementById(inputId);
    if (!input) {
        console.error('Input element not found:', inputId);
        showAlert('Photo input field not found', 'danger');
        return;
    }

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
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

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