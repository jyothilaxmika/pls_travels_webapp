(function() {
    'use strict';

    // Application state
    let currentTab = 'login';
    let currentStep = 'form';
    let otpTimer = 30;
    let timerInterval;
    let userPhone = '';
    let authType = 'login';

    // DOM Elements
    const elements = {
        loginTab: document.getElementById('loginTab'),
        signupTab: document.getElementById('signupTab'),
        loginForm: document.getElementById('loginForm'),
        signupForm: document.getElementById('signupForm'),
        otpVerification: document.getElementById('otpVerification'),
        loginFormElement: document.getElementById('loginFormElement'),
        signupFormElement: document.getElementById('signupFormElement'),
        otpForm: document.getElementById('otpForm'),
        statusMessages: document.getElementById('statusMessages'),
        otpPhoneDisplay: document.getElementById('otpPhoneDisplay'),
        countdown: document.getElementById('countdown'),
        otpTimer: document.getElementById('otpTimer'),
        resendOtp: document.getElementById('resendOtp'),
        verifyOtp: document.getElementById('verifyOtp'),
        verifyText: document.getElementById('verifyText'),
        verifyIcon: document.getElementById('verifyIcon'),
        verifyLoader: document.getElementById('verifyLoader'),
        goBackBtn: document.getElementById('goBackBtn')
    };

    // Initialize the application
    function init() {
        setupEventListeners();
        setupTabSwitching();
        setupOTPInputs();
        setInitialTab();
    }

    function setupEventListeners() {
        // Tab switching
        elements.loginTab.addEventListener('click', () => switchTab('login'));
        elements.signupTab.addEventListener('click', () => switchTab('signup'));

        // Form submissions
        elements.loginFormElement.addEventListener('submit', handleLoginSubmit);
        elements.signupFormElement.addEventListener('submit', handleSignupSubmit);
        elements.otpForm.addEventListener('submit', handleOTPSubmit);

        // Other buttons
        elements.resendOtp.addEventListener('click', handleResendOTP);
        elements.goBackBtn.addEventListener('click', goBack);

        // Switch to login from signup
        const switchToLoginBtn = document.querySelector('[data-testid="link-switch-login"]');
        if (switchToLoginBtn) {
            switchToLoginBtn.addEventListener('click', () => switchTab('login'));
        }
    }

    function setupTabSwitching() {
        function switchTab(tab) {
            currentTab = tab;
            authType = tab;
            
            // Update tab buttons
            document.querySelectorAll('.tab-button').forEach(btn => {
                btn.classList.remove('active');
            });
            
            const activeTab = document.getElementById(tab + 'Tab');
            activeTab.classList.add('active');
            
            // Update form visibility
            document.querySelectorAll('.auth-form').forEach(form => {
                form.classList.add('hidden');
                form.classList.remove('active');
            });
            
            const activeForm = document.getElementById(tab + 'Form');
            activeForm.classList.remove('hidden');
            activeForm.classList.add('active');
            
            // Hide OTP form if visible
            elements.otpVerification.classList.add('hidden');
            currentStep = 'form';
        }

        window.switchTab = switchTab;
    }

    function setupOTPInputs() {
        const otpInputs = document.querySelectorAll('.otp-input');
        
        otpInputs.forEach((input, index) => {
            input.addEventListener('input', function(e) {
                const value = e.target.value;
                
                if (value.length === 1 && /^[0-9]$/.test(value)) {
                    input.classList.add('filled');
                    
                    // Move to next input
                    if (index < otpInputs.length - 1) {
                        otpInputs[index + 1].focus();
                    }
                    
                    checkOTPComplete();
                } else if (value.length === 0) {
                    input.classList.remove('filled');
                    checkOTPComplete();
                } else {
                    // Invalid character, clear it
                    e.target.value = '';
                }
            });

            input.addEventListener('keydown', function(e) {
                // Handle backspace
                if (e.key === 'Backspace' && input.value === '' && index > 0) {
                    otpInputs[index - 1].focus();
                }
                
                // Handle paste
                if (e.key === 'v' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    navigator.clipboard.readText().then(text => {
                        const digits = text.replace(/\D/g, '').slice(0, 6);
                        if (digits.length === 6) {
                            otpInputs.forEach((inp, i) => {
                                inp.value = digits[i] || '';
                                if (digits[i]) inp.classList.add('filled');
                                else inp.classList.remove('filled');
                            });
                            checkOTPComplete();
                        }
                    }).catch(() => {});
                }
            });
        });
    }

    function setInitialTab() {
        const urlPath = window.location.pathname;
        if (urlPath.includes('signup')) {
            switchTab('signup');
        } else {
            switchTab('login');
        }
    }

    function handleLoginSubmit(e) {
        e.preventDefault();
        const phoneInput = document.getElementById('loginPhone');
        const phone = phoneInput.value.trim();
        
        if (!phone) {
            showMessage('Please enter your phone number', 'error');
            return;
        }
        
        if (!isValidPhone(phone)) {
            showMessage('Please enter a valid phone number', 'error');
            return;
        }
        
        sendOTP('login', { phoneNumber: phone });
    }

    function handleSignupSubmit(e) {
        e.preventDefault();
        const nameInput = document.getElementById('signupName');
        const phoneInput = document.getElementById('signupPhone');
        const emailInput = document.getElementById('signupEmail');
        
        const name = nameInput.value.trim();
        const phone = phoneInput.value.trim();
        const email = emailInput.value.trim();
        
        if (!name) {
            showMessage('Please enter your full name', 'error');
            return;
        }
        
        if (!phone) {
            showMessage('Please enter your phone number', 'error');
            return;
        }
        
        if (!isValidPhone(phone)) {
            showMessage('Please enter a valid phone number', 'error');
            return;
        }
        
        if (email && !isValidEmail(email)) {
            showMessage('Please enter a valid email address', 'error');
            return;
        }
        
        sendOTP('signup', { 
            phoneNumber: phone, 
            fullName: name, 
            email: email 
        });
    }

    function handleOTPSubmit(e) {
        e.preventDefault();
        verifyOTP();
    }

    function handleResendOTP() {
        resendOTP();
    }

    async function sendOTP(type, data) {
        authType = type;
        userPhone = data.phoneNumber;
        
        // Show loading state
        const button = document.getElementById(type + 'SendOtp');
        const originalText = button.innerHTML;
        button.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner"></i></div> Sending...';
        button.disabled = true;
        
        try {
            const response = await fetch('/auth/send-otp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    phoneNumber: data.phoneNumber,
                    type: type,
                    fullName: data.fullName,
                    email: data.email
                })
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                showOTPForm();
                showMessage(result.message || 'OTP sent to your phone number', 'success');
                
                // Update phone display
                if (result.maskedPhone) {
                    elements.otpPhoneDisplay.textContent = result.maskedPhone;
                }
            } else {
                showMessage(result.error || 'Failed to send OTP', 'error');
            }
        } catch (error) {
            console.error('Error sending OTP:', error);
            showMessage('Network error. Please try again.', 'error');
        } finally {
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }

    async function verifyOTP() {
        const otpInputs = document.querySelectorAll('.otp-input');
        const otp = Array.from(otpInputs).map(input => input.value).join('');
        
        if (otp.length !== 6) {
            showMessage('Please enter the complete OTP', 'error');
            return;
        }
        
        // Show loading state
        elements.verifyText.textContent = 'Verifying...';
        elements.verifyIcon.classList.add('hidden');
        elements.verifyLoader.classList.remove('hidden');
        elements.verifyOtp.disabled = true;
        
        try {
            const response = await fetch('/auth/verify-otp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    phoneNumber: userPhone,
                    code: otp,
                    type: authType
                })
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                showMessage(result.message || 'Verification successful! Redirecting...', 'success');
                
                // Redirect after successful verification
                setTimeout(() => {
                    window.location.href = result.redirectUrl || '/dashboard';
                }, 1500);
            } else {
                showMessage(result.error || 'Invalid OTP. Please try again.', 'error');
                
                // Clear OTP inputs
                otpInputs.forEach(input => {
                    input.value = '';
                    input.classList.remove('filled');
                });
                
                document.getElementById('otp1').focus();
                checkOTPComplete();
            }
        } catch (error) {
            console.error('Error verifying OTP:', error);
            showMessage('Network error. Please try again.', 'error');
        } finally {
            elements.verifyText.textContent = 'Verify & Continue';
            elements.verifyIcon.classList.remove('hidden');
            elements.verifyLoader.classList.add('hidden');
            elements.verifyOtp.disabled = false;
        }
    }

    async function resendOTP() {
        if (!userPhone) {
            showMessage('No phone number found. Please start over.', 'error');
            return;
        }

        try {
            const response = await fetch('/auth/resend-otp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    phoneNumber: userPhone
                })
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                // Clear OTP inputs
                document.querySelectorAll('.otp-input').forEach(input => {
                    input.value = '';
                    input.classList.remove('filled');
                });
                
                startOTPTimer();
                showMessage(result.message || 'OTP resent to your phone number', 'success');
                document.getElementById('otp1').focus();
                checkOTPComplete();
            } else {
                showMessage(result.error || 'Failed to resend OTP', 'error');
            }
        } catch (error) {
            console.error('Error resending OTP:', error);
            showMessage('Network error. Please try again.', 'error');
        }
    }

    function showOTPForm() {
        document.querySelectorAll('.auth-form').forEach(form => {
            form.classList.add('hidden');
        });
        
        elements.otpVerification.classList.remove('hidden');
        
        // Focus first OTP input
        document.getElementById('otp1').focus();
        
        // Start countdown timer
        startOTPTimer();
        currentStep = 'otp';
    }

    function goBack() {
        elements.otpVerification.classList.add('hidden');
        document.getElementById(authType + 'Form').classList.remove('hidden');
        clearInterval(timerInterval);
        currentStep = 'form';
        
        // Clear OTP inputs
        document.querySelectorAll('.otp-input').forEach(input => {
            input.value = '';
            input.classList.remove('filled');
        });
        
        checkOTPComplete();
    }

    function checkOTPComplete() {
        const otpInputs = document.querySelectorAll('.otp-input');
        const otp = Array.from(otpInputs).map(input => input.value).join('');
        
        elements.verifyOtp.disabled = otp.length !== 6;
    }

    function startOTPTimer() {
        otpTimer = 30;
        elements.countdown.textContent = otpTimer;
        elements.otpTimer.classList.remove('hidden');
        elements.resendOtp.classList.add('hidden');
        
        timerInterval = setInterval(() => {
            otpTimer--;
            elements.countdown.textContent = otpTimer;
            
            if (otpTimer <= 0) {
                clearInterval(timerInterval);
                elements.otpTimer.classList.add('hidden');
                elements.resendOtp.classList.remove('hidden');
            }
        }, 1000);
    }

    function isValidPhone(phone) {
        const phoneRegex = /^\+?[1-9]\d{1,14}$/;
        return phoneRegex.test(phone.replace(/\s/g, ''));
    }

    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    function showMessage(message, type = 'info') {
        const messageEl = document.createElement('div');
        
        const statusClass = type === 'error' ? 'status-error' : 
                           type === 'success' ? 'status-success' : 'status-info';
        
        const iconClass = type === 'error' ? 'exclamation-circle' : 
                         type === 'success' ? 'check-circle' : 'info-circle';
        
        messageEl.className = `${statusClass} px-4 py-3 rounded-lg flex items-center space-x-2 slide-in`;
        messageEl.innerHTML = `
            <i class="fas fa-${iconClass}"></i>
            <span class="flex-1">${message}</span>
            <button onclick="this.parentElement.remove()" class="text-white/80 hover:text-white">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        elements.statusMessages.appendChild(messageEl);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (messageEl.parentElement) {
                messageEl.remove();
            }
        }, 5000);
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
