// Duty management JavaScript functionality for PLS TRAVELS Driver Portal

document.addEventListener('DOMContentLoaded', function() {
    initializeDutyManagement();
});

function initializeDutyManagement() {
    setupPhotoCapture();
    setupFormValidation();
    setupDurationTracking();
    setupRevenueCalculation();  // Use the new revenue calculation instead of earnings
    setupOfflineSupport();
    setupTrackingPauseControls();  // Add pause/resume tracking functionality
}

// Photo capture and preview functionality
function setupPhotoCapture() {
    const photoInputs = document.querySelectorAll('input[type="file"][accept*="image"]');
    
    photoInputs.forEach(input => {
        input.addEventListener('change', handlePhotoCapture);
        
        // Add camera button for better mobile UX
        addCameraButton(input);
    });
}

function handlePhotoCapture(event) {
    const file = event.target.files[0];
    const input = event.target;
    
    if (file) {
        // Validate file size (max 5MB)
        if (file.size > 5 * 1024 * 1024) {
            showAlert('Photo size must be less than 5MB', 'warning');
            input.value = '';
            return;
        }
        
        // Validate file type
        if (!file.type.startsWith('image/')) {
            showAlert('Please select a valid image file', 'warning');
            input.value = '';
            return;
        }
        
        // Capture GPS location and timestamp
        captureLocationAndTimestamp(file, input);
        
        // Create preview
        createPhotoPreview(file, input);
        
        // Compress image if needed
        if (file.size > 1024 * 1024) { // 1MB
            compressImage(file, input);
        }
    }
}

function createPhotoPreview(file, input) {
    const reader = new FileReader();
    reader.onload = function(e) {
        let previewContainer = input.parentNode.querySelector('.photo-preview');
        
        if (!previewContainer) {
            previewContainer = document.createElement('div');
            previewContainer.className = 'photo-preview mt-2';
            input.parentNode.appendChild(previewContainer);
        }
        
        // Clear previous content
        previewContainer.textContent = '';
        
        // Create container div
        const containerDiv = document.createElement('div');
        containerDiv.className = 'position-relative d-inline-block';
        
        // Create image element
        const img = document.createElement('img');
        img.src = e.target.result;
        img.className = 'img-fluid rounded shadow';
        img.style.maxHeight = '200px';
        containerDiv.appendChild(img);
        
        // Create remove button
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'btn btn-sm btn-danger position-absolute top-0 end-0 mt-1 me-1';
        removeBtn.addEventListener('click', function() {
            removePhoto(this, input.id);
        });
        
        // Create button icon
        const icon = document.createElement('i');
        icon.className = 'fas fa-times';
        removeBtn.appendChild(icon);
        containerDiv.appendChild(removeBtn);
        
        // Create success message with timestamp
        const successMsg = document.createElement('small');
        successMsg.className = 'd-block text-success mt-1';
        
        const successIcon = document.createElement('i');
        successIcon.className = 'fas fa-check-circle';
        successMsg.appendChild(successIcon);
        
        const timestamp = new Date().toLocaleString();
        successMsg.appendChild(document.createTextNode(` Photo captured at ${timestamp}`));
        
        // Append all elements
        previewContainer.appendChild(containerDiv);
        previewContainer.appendChild(successMsg);
    };
    reader.readAsDataURL(file);
}

function removePhoto(button, inputId) {
    const input = document.getElementById(inputId);
    if (!input) {
        console.error('Input element not found:', inputId);
        return;
    }
    
    const previewContainer = button.closest('.photo-preview');
    if (!previewContainer) {
        console.error('Preview container not found');
        return;
    }
    
    input.value = '';
    previewContainer.remove();
    
    // Remove associated validation fields for odometer photos
    if (inputId.includes('odometer')) {
        const timestampField = input.parentNode.querySelector(`input[name*="photo_timestamp"]`);
        const capturedField = input.parentNode.querySelector(`input[name*="${inputId}_captured"]`);
        
        if (timestampField) timestampField.remove();
        if (capturedField) capturedField.remove();
        
        // Show waiting status again
        const photoType = inputId.includes('start') ? 'start' : 'end';
        const statusDiv = document.getElementById(`${photoType}_photo_status`);
        if (statusDiv) {
            statusDiv.classList.remove('d-none');
        }
    }
}

function addCameraButton(input) {
    const cameraBtn = document.createElement('button');
    cameraBtn.type = 'button';
    cameraBtn.className = 'btn btn-outline-primary btn-sm mt-2';
    // Create icon element safely
    const cameraIcon = document.createElement('i');
    cameraIcon.className = 'fas fa-camera me-1';
    cameraBtn.appendChild(cameraIcon);
    cameraBtn.appendChild(document.createTextNode('Open Camera'));
    
    cameraBtn.addEventListener('click', function() {
        input.click();
    });
    
    input.parentNode.appendChild(cameraBtn);
}

// GPS Location and Timestamp Capture
function captureLocationAndTimestamp(file, input) {
    const timestamp = new Date().toISOString();
    const inputType = input.id.includes('start') ? 'start' : 'end';
    
    // Validate timestamp freshness for odometer photos
    const isOdometerPhoto = input.id.includes('odometer');
    if (isOdometerPhoto) {
        // Check if photo is recent (within last 2 minutes for freshness)
        const photoTimestamp = file.lastModified || Date.now();
        const now = Date.now();
        const timeDiff = now - photoTimestamp;
        const maxAge = 2 * 60 * 1000; // 2 minutes in milliseconds
        
        if (timeDiff > maxAge) {
            showAlert('⚠️ Please take a fresh photo of the odometer reading. Old photos are not accepted for verification.', 'warning');
            input.value = '';
            return;
        }
    }
    
    // Store timestamp immediately
    const existingTimestamp = input.parentNode.querySelector(`input[name="${inputType}_photo_timestamp"]`);
    if (existingTimestamp) {
        existingTimestamp.remove();
    }
    
    const timestampField = document.createElement('input');
    timestampField.type = 'hidden';
    timestampField.name = `${inputType}_photo_timestamp`;
    timestampField.value = timestamp;
    input.parentNode.appendChild(timestampField);
    
    // Store file data for validation
    if (isOdometerPhoto) {
        const photoDataField = document.createElement('input');
        photoDataField.type = 'hidden';
        photoDataField.name = `${input.id}_captured`;
        photoDataField.value = 'true';
        input.parentNode.appendChild(photoDataField);
    }
    
    // Location capture removed per user request
    // Show that photo was captured successfully with timestamp
    const timeStr = new Date(timestamp).toLocaleTimeString();
    showLocationStatus(input.parentNode, `📸 Photo captured at ${timeStr}`, 'success');
}

function showLocationStatus(container, message, type = 'info') {
    // Remove existing status
    const existingStatus = container.querySelector('.location-status');
    if (existingStatus) {
        existingStatus.remove();
    }
    
    // Create status element
    const statusDiv = document.createElement('div');
    statusDiv.className = `location-status alert alert-${type} alert-sm mt-2 py-1 px-2`;
    statusDiv.style.fontSize = '0.75rem';
    
    const icon = type === 'success' ? 'fa-map-marker-alt' : 
                 type === 'warning' ? 'fa-exclamation-triangle' : 
                 'fa-spinner fa-spin';
    
    // Create icon element safely
    const iconElement = document.createElement('i');
    iconElement.className = `fas ${icon} me-1`;
    
    // Add content safely using textContent
    statusDiv.appendChild(iconElement);
    statusDiv.appendChild(document.createTextNode(message));
    container.appendChild(statusDiv);
    
    // Auto-remove after 3 seconds for success messages, longer for others
    const removeDelay = type === 'success' ? 3000 : type === 'info' ? 5000 : 0;
    if (removeDelay > 0) {
        setTimeout(() => {
            if (statusDiv.parentNode) {
                statusDiv.remove();
            }
        }, removeDelay);
    }
}

// Image compression for better performance
function compressImage(file, input) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();
    
    img.onload = function() {
        // Calculate new dimensions (max 1200px width)
        let { width, height } = img;
        const maxWidth = 1200;
        
        if (width > maxWidth) {
            height = (height * maxWidth) / width;
            width = maxWidth;
        }
        
        canvas.width = width;
        canvas.height = height;
        
        // Draw and compress
        ctx.drawImage(img, 0, 0, width, height);
        
        canvas.toBlob(function(blob) {
            // Replace original file with compressed version
            const compressedFile = new File([blob], file.name, {
                type: 'image/jpeg',
                lastModified: Date.now()
            });
            
            // Update input with compressed file
            const dt = new DataTransfer();
            dt.items.add(compressedFile);
            input.files = dt.files;
            
            console.log(`Image compressed: ${(file.size / 1024).toFixed(0)}KB → ${(blob.size / 1024).toFixed(0)}KB`);
        }, 'image/jpeg', 0.8);
    };
    
    img.src = URL.createObjectURL(file);
}

// Form validation for duty operations
function setupFormValidation() {
    const dutyForms = document.querySelectorAll('form[action*="duty"]');
    
    dutyForms.forEach(form => {
        form.addEventListener('submit', validateDutyForm);
        
        // Real-time validation
        const inputs = form.querySelectorAll('input, select');
        inputs.forEach(input => {
            input.addEventListener('blur', validateField);
        });
    });
}

function validateDutyForm(event) {
    const form = event.target;
    let isValid = true;
    
    // Validate required fields
    const requiredFields = form.querySelectorAll('[required]');
    requiredFields.forEach(field => {
        if (!validateField({ target: field })) {
            isValid = false;
        }
    });
    
    // Validate mandatory odometer photos
    if (!validateOdometerPhotos(form)) {
        isValid = false;
    }
    
    // Specific validations
    if (form.action.includes('start_duty')) {
        isValid = validateStartDuty(form) && isValid;
    } else if (form.action.includes('end_duty')) {
        isValid = validateEndDuty(form) && isValid;
    }
    
    if (!isValid) {
        event.preventDefault();
        showAlert('Please correct the errors and try again', 'danger');
        
        // Scroll to first error
        const firstError = form.querySelector('.is-invalid');
        if (firstError) {
            firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            firstError.focus();
        }
    }
    
    return isValid;
}

function validateField(event) {
    const field = event.target;
    const value = field.value.trim();
    let isValid = true;
    
    // Remove existing validation classes
    field.classList.remove('is-valid', 'is-invalid');
    
    // Required field validation
    if (field.hasAttribute('required') && !value) {
        setFieldError(field, 'This field is required');
        isValid = false;
    }
    
    // Type-specific validations
    if (isValid && value) {
        switch (field.type) {
            case 'number':
                isValid = validateNumberField(field);
                break;
            case 'file':
                isValid = validateFileField(field);
                break;
        }
    }
    
    if (isValid) {
        field.classList.add('is-valid');
    }
    
    return isValid;
}

function validateNumberField(field) {
    const value = parseFloat(field.value);
    const min = parseFloat(field.getAttribute('min'));
    const max = parseFloat(field.getAttribute('max'));
    
    if (isNaN(value)) {
        setFieldError(field, 'Please enter a valid number');
        return false;
    }
    
    if (min !== null && value < min) {
        setFieldError(field, `Value must be at least ${min}`);
        return false;
    }
    
    if (max !== null && value > max) {
        setFieldError(field, `Value must not exceed ${max}`);
        return false;
    }
    
    // Odometer validation
    if (field.id === 'end_odometer') {
        const startOdometer = document.getElementById('start_odometer');
        if (startOdometer && value <= parseFloat(startOdometer.value)) {
            setFieldError(field, 'End reading must be greater than start reading');
            return false;
        }
    }
    
    return true;
}

function validateFileField(field) {
    if (field.files.length === 0) {
        if (field.hasAttribute('required')) {
            setFieldError(field, 'Please select a file');
            return false;
        }
        return true;
    }
    
    const file = field.files[0];
    
    // File size check (5MB max)
    if (file.size > 5 * 1024 * 1024) {
        setFieldError(field, 'File size must be less than 5MB');
        return false;
    }
    
    // File type check for images
    if (field.accept && field.accept.includes('image') && !file.type.startsWith('image/')) {
        setFieldError(field, 'Please select a valid image file');
        return false;
    }
    
    return true;
}

function validateStartDuty(form) {
    const vehicleSelect = form.querySelector('#vehicle_id');
    const odometerInput = form.querySelector('#start_odometer');
    const photoInput = form.querySelector('#start_odometer_photo');
    
    let isValid = true;
    
    // Vehicle selection
    if (!vehicleSelect.value) {
        setFieldError(vehicleSelect, 'Please select a vehicle');
        isValid = false;
    }
    
    // Odometer reading
    if (!odometerInput.value || parseFloat(odometerInput.value) < 0) {
        setFieldError(odometerInput, 'Please enter a valid odometer reading');
        isValid = false;
    }
    
    // Mandatory odometer photo with timestamp validation
    if (!photoInput.value) {
        setFieldError(document.querySelector('.capture-photo-btn'), 'Start odometer photo is mandatory. Please capture a clear photo of the current odometer reading.');
        isValid = false;
    } else {
        // Check if photo was taken recently (within last 10 minutes)
        const photoTimestamp = photoInput.getAttribute('data-timestamp');
        if (photoTimestamp) {
            const photoTime = new Date(parseInt(photoTimestamp));
            const currentTime = new Date();
            const timeDiff = (currentTime - photoTime) / (1000 * 60); // difference in minutes
            
            if (timeDiff > 10) {
                setFieldError(document.querySelector('.capture-photo-btn'), 'Start odometer photo is mandatory. Please capture a clear photo of the current odometer reading.');
                isValid = false;
            }
        }
    }
    
    return isValid;
}

function validateEndDuty(form) {
    const endOdometerInput = form.querySelector('#end_odometer');
    const endCngInput = form.querySelector('#end_cng');
    
    let isValid = true;
    
    // End odometer validation
    const startOdometer = parseFloat(endOdometerInput.getAttribute('min') || 0);
    const endOdometer = parseFloat(endOdometerInput.value || 0);
    
    if (endOdometer <= startOdometer) {
        setFieldError(endOdometerInput, 'End reading must be greater than start reading');
        isValid = false;
    }
    
    // CNG level validation
    if (!endCngInput.value) {
        setFieldError(endCngInput, 'Please select end CNG level');
        isValid = false;
    }
    
    return isValid;
}

function setFieldError(field, message) {
    field.classList.add('is-invalid');
    
    // Remove existing error message
    const existingError = field.parentNode.querySelector('.invalid-feedback');
    if (existingError) {
        existingError.remove();
    }
    
    // Add new error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;
    field.parentNode.appendChild(errorDiv);
}

// Validate mandatory odometer photos with timestamp validation
function validateOdometerPhotos(form) {
    let isValid = true;
    
    // Check for start duty - requires start odometer photo
    if (form.action.includes('start_duty')) {
        const startOdometerPhoto = form.querySelector('#start_odometer_photo');
        if (startOdometerPhoto) {
            const photoCaptured = form.querySelector('input[name="start_odometer_photo_captured"]');
            const photoTimestamp = form.querySelector('input[name="start_photo_timestamp"]');
            
            if (!photoCaptured || !photoTimestamp) {
                showPhotoError('start_odometer_photo_container', '📸 Start odometer photo is required. Please capture a fresh photo of the odometer reading.');
                isValid = false;
            } else {
                // Validate timestamp is recent (within last 5 minutes)
                const captureTime = new Date(photoTimestamp.value);
                const now = new Date();
                const timeDiff = (now - captureTime) / (1000 * 60); // minutes
                
                if (timeDiff > 5) {
                    showPhotoError('start_odometer_photo_container', '⏰ Start odometer photo is too old. Please capture a fresh photo.');
                    isValid = false;
                }
            }
        }
    }
    
    // Check for end duty - requires end odometer photo
    if (form.action.includes('end_duty')) {
        const endOdometerPhoto = form.querySelector('#end_odometer_photo');
        if (endOdometerPhoto) {
            const photoCaptured = form.querySelector('input[name="end_odometer_photo_captured"]');
            const photoTimestamp = form.querySelector('input[name="end_photo_timestamp"]');
            
            if (!photoCaptured || !photoTimestamp) {
                showPhotoError('end_odometer_photo_container', '📸 End odometer photo is required. Please capture a fresh photo of the final odometer reading.');
                isValid = false;
            } else {
                // Validate timestamp is recent (within last 5 minutes)
                const captureTime = new Date(photoTimestamp.value);
                const now = new Date();
                const timeDiff = (now - captureTime) / (1000 * 60); // minutes
                
                if (timeDiff > 5) {
                    showPhotoError('end_odometer_photo_container', '⏰ End odometer photo is too old. Please capture a fresh photo.');
                    isValid = false;
                }
            }
        }
    }
    
    return isValid;
}

function showPhotoError(containerId, message) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    // Remove existing error
    const existingError = container.querySelector('.photo-error');
    if (existingError) {
        existingError.remove();
    }
    
    // Add new error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'photo-error alert alert-danger mt-2';
    errorDiv.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i>${message}`;
    container.appendChild(errorDiv);
    
    // Scroll to error
    container.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// Duration tracking for active duties
function setupDurationTracking() {
    const durationElement = document.getElementById('duty-duration');
    if (durationElement) {
        updateDurationDisplay();
        setInterval(updateDurationDisplay, 60000); // Update every minute
    }
}

function updateDurationDisplay() {
    const durationElement = document.getElementById('duty-duration');
    if (!durationElement) return;
    
    // This would be populated from server-side data
    const startTimeStr = durationElement.getAttribute('data-start-time');
    if (!startTimeStr) return;
    
    const startTime = new Date(startTimeStr);
    const now = new Date();
    const diff = now - startTime;
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
}

// Real-time revenue calculation for simplified revenue form
function setupRevenueCalculation() {
    const platformCash = document.getElementById('platform_cash');
    const platformDigital = document.getElementById('platform_digital');
    const directCash = document.getElementById('direct_cash');
    const directDigital = document.getElementById('direct_digital');
    
    if (platformCash && platformDigital && directCash && directDigital) {
        [platformCash, platformDigital, directCash, directDigital].forEach(input => {
            input.addEventListener('input', updateRevenueTotals);
        });
    }
}

function updateRevenueTotals() {
    const platformCash = parseFloat(document.getElementById('platform_cash')?.value || 0);
    const platformDigital = parseFloat(document.getElementById('platform_digital')?.value || 0);
    const directCash = parseFloat(document.getElementById('direct_cash')?.value || 0);
    const directDigital = parseFloat(document.getElementById('direct_digital')?.value || 0);
    
    const platformTotal = platformCash + platformDigital;
    const directTotal = directCash + directDigital;
    const grandTotal = platformTotal + directTotal;
    
    // Update display elements
    const platformTotalElement = document.getElementById('platform_total');
    const directTotalElement = document.getElementById('direct_total');
    const grandTotalElement = document.getElementById('grand_total');
    
    if (platformTotalElement) platformTotalElement.textContent = platformTotal.toFixed(2);
    if (directTotalElement) directTotalElement.textContent = directTotal.toFixed(2);
    if (grandTotalElement) grandTotalElement.textContent = grandTotal.toFixed(2);
    
    // Basic anomaly detection
    performRevenueAnomalyCheck(grandTotal, platformTotal, directTotal);
}

function performRevenueAnomalyCheck(grandTotal, platformTotal, directTotal) {
    const warningContainer = document.getElementById('revenue_warning');
    let warnings = [];
    
    // Remove existing warnings
    if (warningContainer) {
        warningContainer.remove();
    }
    
    // Check for unusual patterns
    if (grandTotal > 5000) {
        warnings.push('⚠️ High revenue detected. Please verify all amounts.');
    }
    
    if (directTotal > platformTotal * 2 && platformTotal > 0) {
        warnings.push('⚠️ Direct revenue significantly higher than platform revenue. Please verify.');
    }
    
    if (grandTotal > 0 && platformTotal === 0 && directTotal === 0) {
        warnings.push('⚠️ Total revenue calculated but no individual amounts entered.');
    }
    
    // Show warnings if any
    if (warnings.length > 0) {
        const alertDiv = document.createElement('div');
        alertDiv.id = 'revenue_warning';
        alertDiv.className = 'alert alert-warning mt-2';
        alertDiv.innerHTML = `
            <i class="fas fa-exclamation-triangle me-2"></i>
            <strong>Revenue Check:</strong><br>
            ${warnings.join('<br>')}
        `;
        
        const revenueCard = document.querySelector('.card.border-primary');
        if (revenueCard) {
            revenueCard.appendChild(alertDiv);
        }
}

// Initialize revenue calculation on page load
document.addEventListener('DOMContentLoaded', function() {
    setupRevenueCalculation();
});

// Real-time earnings calculation
function setupEarningsCalculation() {
    // Removed - earnings calculations are handled server-side only
}

// Removed - earnings calculations are server-side only

// Offline support for duty data
function setupOfflineSupport() {
    // Store duty data locally when offline
    if ('serviceWorker' in navigator && 'caches' in window) {
        // Basic offline support
        window.addEventListener('offline', handleOffline);
        window.addEventListener('online', handleOnline);
    }
}

function handleOffline() {
    showAlert('You are offline. Data will be saved locally and synced when reconnected.', 'info');
    
    // Store form data in localStorage
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);
        localStorage.setItem(`duty_form_${form.id}`, JSON.stringify(data));
    });
}

function handleOnline() {
    showAlert('Connection restored. Syncing data...', 'success');
    
    // Sync stored data
    syncOfflineData();
}

function syncOfflineData() {
    // Check for stored form data and attempt to submit
    Object.keys(localStorage).forEach(key => {
        if (key.startsWith('duty_form_')) {
            const data = JSON.parse(localStorage.getItem(key));
            // Implement sync logic here
            localStorage.removeItem(key);
        }
    });
}

// Utility functions
function showAlert(message, type = 'info') {
    const alertContainer = getAlertContainer();
    const alertId = 'alert_' + Date.now();
    
    // Create alert element safely
    const alertDiv = document.createElement('div');
    alertDiv.id = alertId;
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.setAttribute('role', 'alert');
    
    // Create icon
    const iconElement = document.createElement('i');
    iconElement.className = `fas fa-${getAlertIcon(type)} me-2`;
    alertDiv.appendChild(iconElement);
    
    // Add message safely
    alertDiv.appendChild(document.createTextNode(message));
    
    // Create close button
    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'btn-close';
    closeBtn.setAttribute('data-bs-dismiss', 'alert');
    alertDiv.appendChild(closeBtn);
    
    alertContainer.appendChild(alertDiv);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alertElement = document.getElementById(alertId);
        if (alertElement) {
            const bsAlert = new bootstrap.Alert(alertElement);
            bsAlert.close();
        }
    }, 5000);
}

function getAlertContainer() {
    let container = document.getElementById('duty-alerts');
    if (!container) {
        container = document.createElement('div');
        container.id = 'duty-alerts';
        container.className = 'position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    return container;
}

function getAlertIcon(type) {
    const icons = {
        success: 'check-circle',
        danger: 'exclamation-triangle',
        warning: 'exclamation-circle',
        info: 'info-circle'
    };
    return icons[type] || 'info-circle';
}

function formatCurrency(amount) {
    return '₹' + amount.toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// GPS location tracking (optional enhancement)
function trackLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            position => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                
                // Store location for duty verification
                sessionStorage.setItem('duty_location', JSON.stringify({ lat, lng, timestamp: Date.now() }));
            },
            error => {
                console.log('Location access denied:', error);
            }
        );
    }
}

// Initialize location tracking on duty start
document.addEventListener('DOMContentLoaded', function() {
    const startDutyBtn = document.querySelector('button[type="submit"]');
    if (startDutyBtn && startDutyBtn.textContent.includes('Start Duty')) {
        trackLocation();
    }
});

// Tracking Pause Controls Functionality
function setupTrackingPauseControls() {
    const pauseBtn = document.getElementById('pauseTrackingBtn');
    const resumeBtn = document.getElementById('resumeTrackingBtn');
    
    if (pauseBtn && resumeBtn) {
        pauseBtn.addEventListener('click', pauseTracking);
        resumeBtn.addEventListener('click', resumeTracking);
        
        // Initialize tracking status
        loadTrackingStatus();
        
        // Update status every 30 seconds
        setInterval(loadTrackingStatus, 30000);
    }
}

function loadTrackingStatus() {
    fetch('/driver/duty/tracking-status', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateTrackingUI(data.pause_status);
            
            // Show auto-resume notification if tracking was auto-resumed
            if (data.pause_status.auto_resumed) {
                showAlert('Tracking automatically resumed after 10-minute limit', 'info');
            }
        }
    })
    .catch(error => {
        console.log('Error loading tracking status:', error);
    });
}

function pauseTracking() {
    const pauseReason = prompt('Why are you pausing location tracking?', 'Privacy break') || 'Privacy break';
    
    fetch('/driver/duty/pause-tracking', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            reason: pauseReason
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert(data.message, 'success');
            updateTrackingUI(data.pause_status);
            startPauseTimer();
        } else {
            showAlert(data.error || 'Failed to pause tracking', 'danger');
        }
    })
    .catch(error => {
        console.error('Error pausing tracking:', error);
        showAlert('Network error - failed to pause tracking', 'danger');
    });
}

function resumeTracking() {
    fetch('/driver/duty/resume-tracking', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert(data.message, 'success');
            updateTrackingUI(data.pause_status);
            stopPauseTimer();
        } else {
            showAlert(data.error || 'Failed to resume tracking', 'danger');
        }
    })
    .catch(error => {
        console.error('Error resuming tracking:', error);
        showAlert('Network error - failed to resume tracking', 'danger');
    });
}

function updateTrackingUI(pauseStatus) {
    const activeBadge = document.getElementById('tracking-active-badge');
    const pausedBadge = document.getElementById('tracking-paused-badge');
    const pausesUsed = document.getElementById('pauses-used');
    const pauseBtn = document.getElementById('pauseTrackingBtn');
    const resumeBtn = document.getElementById('resumeTrackingBtn');
    const pauseTimer = document.getElementById('pause-timer');
    
    if (!activeBadge || !pausedBadge || !pausesUsed || !pauseBtn || !resumeBtn) {
        return; // UI elements not found
    }
    
    // Update pause count display
    pausesUsed.textContent = `${pauseStatus.pauses_used}/3`;
    
    if (pauseStatus.is_paused) {
        // Show paused state
        activeBadge.style.display = 'none';
        pausedBadge.style.display = 'inline-block';
        pauseBtn.style.display = 'none';
        resumeBtn.style.display = 'block';
        pauseTimer.style.display = 'block';
        
        // Start pause timer
        startPauseTimer();
    } else {
        // Show active state
        activeBadge.style.display = 'inline-block';
        pausedBadge.style.display = 'none';
        pauseTimer.style.display = 'none';
        resumeBtn.style.display = 'none';
        
        // Show/hide pause button based on remaining pauses
        if (pauseStatus.remaining_pauses > 0) {
            pauseBtn.style.display = 'block';
            pauseBtn.disabled = false;
            pauseBtn.innerHTML = '<i class="fas fa-pause me-2"></i>Pause Tracking';
        } else {
            pauseBtn.style.display = 'block';
            pauseBtn.disabled = true;
            pauseBtn.innerHTML = '<i class="fas fa-ban me-2"></i>No Pauses Left';
        }
        
        // Stop pause timer
        stopPauseTimer();
    }
}

let pauseTimerInterval;

function startPauseTimer() {
    // Clear existing timer
    stopPauseTimer();
    
    // Start new timer
    pauseTimerInterval = setInterval(updatePauseTimer, 1000);
    updatePauseTimer(); // Update immediately
}

function stopPauseTimer() {
    if (pauseTimerInterval) {
        clearInterval(pauseTimerInterval);
        pauseTimerInterval = null;
    }
}

function updatePauseTimer() {
    // Get current tracking status to calculate remaining time
    fetch('/driver/duty/tracking-status', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.pause_status.is_paused) {
            const remainingTime = data.pause_status.current_pause_time || 0;
            updatePauseTimerDisplay(remainingTime);
            
            // Show auto-resume notification if applicable
            if (data.pause_status.auto_resumed) {
                showAlert('Tracking automatically resumed after 10-minute limit', 'info');
                stopPauseTimer();
                loadTrackingStatus();
            }
        } else {
            // Not paused anymore, stop timer
            stopPauseTimer();
            loadTrackingStatus(); // Refresh UI
        }
    })
    .catch(error => {
        console.log('Error updating pause timer:', error);
    });
}

function updatePauseTimerDisplay(remainingMinutes) {
    const remainingSeconds = Math.max(0, remainingMinutes * 60);
    const minutes = Math.floor(remainingSeconds / 60);
    const seconds = Math.floor(remainingSeconds % 60);
    
    const timeText = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    const progressPercent = Math.max(0, (remainingMinutes / 10) * 100);
    
    const timeDisplay = document.getElementById('pause-time-remaining');
    const progressBar = document.getElementById('pause-progress');
    
    if (timeDisplay) timeDisplay.textContent = timeText;
    if (progressBar) progressBar.style.width = `${progressPercent}%`;
    
    // Auto-resume warning when time is running out
    if (remainingMinutes < 1) {
        const progressBar = document.getElementById('pause-progress');
        if (progressBar) {
            progressBar.classList.add('bg-danger');
            progressBar.classList.remove('bg-warning');
        }
        
        if (remainingMinutes < 0.5) {
            showAlert('Tracking will resume automatically in less than 30 seconds', 'warning');
        }
    }
}

function getCsrfToken() {
    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    if (csrfTokenMeta) {
        return csrfTokenMeta.getAttribute('content');
    }
    
    // Fallback: try to get from form
    const csrfInput = document.querySelector('input[name="csrf_token"]');
    return csrfInput ? csrfInput.value : '';
}
