package com.plstravels.driver.ui.auth

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.plstravels.driver.data.repository.AuthRepository
import com.plstravels.driver.security.SecureBiometricManager
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import timber.log.Timber
import javax.inject.Inject

/**
 * ViewModel for authentication screens
 */
@HiltViewModel
class AuthViewModel @Inject constructor(
    val authRepository: AuthRepository,
    private val secureBiometricManager: SecureBiometricManager
) : ViewModel() {

    // UI State
    var uiState by mutableStateOf(AuthUiState())
        private set

    // Authentication status
    val isLoggedIn: StateFlow<Boolean> = authRepository.isLoggedIn
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = false
        )

    // Current user info
    val currentUser: StateFlow<AuthRepository.UserInfo?> = authRepository.currentUser
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = null
        )

    /**
     * Send OTP to phone number
     */
    fun sendOtp(phone: String) {
        if (uiState.isLoading) return

        // Validate phone number
        if (phone.isBlank() || phone.length < 10) {
            updateUiState(error = "Please enter a valid phone number")
            return
        }

        viewModelScope.launch {
            updateUiState(isLoading = true, error = null)
            
            try {
                val result = authRepository.sendOtp(phone)
                result.fold(
                    onSuccess = { response ->
                        if (response.success) {
                            updateUiState(
                                isLoading = false,
                                otpSent = true,
                                message = response.message,
                                currentPhone = phone
                            )
                        } else {
                            updateUiState(
                                isLoading = false,
                                error = response.error ?: response.message
                            )
                        }
                    },
                    onFailure = { exception ->
                        updateUiState(
                            isLoading = false,
                            error = exception.message ?: "Failed to send OTP"
                        )
                    }
                )
            } catch (e: Exception) {
                Timber.e(e, "Send OTP error")
                updateUiState(
                    isLoading = false,
                    error = "Network error. Please check your connection."
                )
            }
        }
    }

    /**
     * Verify OTP and login
     */
    fun verifyOtp(otp: String, deviceInfo: String? = null, fcmToken: String? = null) {
        if (uiState.isLoading) return
        
        val phone = uiState.currentPhone
        if (phone.isBlank()) {
            updateUiState(error = "Phone number is required")
            return
        }

        // Validate OTP
        if (otp.isBlank() || otp.length != 6) {
            updateUiState(error = "Please enter a valid 6-digit OTP")
            return
        }

        viewModelScope.launch {
            updateUiState(isLoading = true, error = null)
            
            try {
                val result = authRepository.verifyOtp(phone, otp, deviceInfo, fcmToken)
                result.fold(
                    onSuccess = { response ->
                        if (response.success) {
                            updateUiState(
                                isLoading = false,
                                loginSuccessful = true,
                                message = "Login successful!"
                            )
                        } else {
                            updateUiState(
                                isLoading = false,
                                error = response.error ?: response.message ?: "Invalid OTP"
                            )
                        }
                    },
                    onFailure = { exception ->
                        updateUiState(
                            isLoading = false,
                            error = exception.message ?: "Failed to verify OTP"
                        )
                    }
                )
            } catch (e: Exception) {
                Timber.e(e, "Verify OTP error")
                updateUiState(
                    isLoading = false,
                    error = "Network error. Please check your connection."
                )
            }
        }
    }

    /**
     * Logout user with biometric cleanup
     */
    fun logout() {
        viewModelScope.launch {
            updateUiState(isLoading = true)
            
            try {
                // Get current user info for biometric cleanup
                val currentUser = authRepository.currentUser.first()
                val biometricKeyAlias = authRepository.getBiometricKeyAlias()
                
                // Logout from repository
                authRepository.logout()
                
                // Clean up biometric keys if they exist
                if (!biometricKeyAlias.isNullOrEmpty()) {
                    secureBiometricManager.disableBiometricAuth(biometricKeyAlias)
                    Timber.i("Biometric keys cleaned up during logout")
                }
                
                updateUiState(
                    isLoading = false,
                    otpSent = false,
                    loginSuccessful = false,
                    currentPhone = "",
                    message = "Logged out successfully",
                    biometricAvailable = false
                )
            } catch (e: Exception) {
                Timber.e(e, "Logout error")
                updateUiState(isLoading = false)
            }
        }
    }

    /**
     * Clear error messages
     */
    fun clearError() {
        updateUiState(error = null)
    }

    /**
     * Clear success messages
     */
    fun clearMessage() {
        updateUiState(message = null)
    }

    /**
     * Reset OTP flow (to enter different phone number)
     */
    fun resetOtpFlow() {
        updateUiState(
            otpSent = false,
            currentPhone = "",
            error = null,
            message = null
        )
    }
    
    /**
     * Check biometric availability and update UI state
     */
    fun checkBiometricAvailability() {
        viewModelScope.launch {
            try {
                val availability = secureBiometricManager.getBiometricAvailability()
                val isAvailable = availability == SecureBiometricManager.BiometricAvailability.AVAILABLE
                
                // Check if user has existing biometric setup
                val currentUser = authRepository.currentUser.first()
                val hasExistingBiometric = currentUser != null && 
                    authRepository.isBiometricEnabled.first() &&
                    !authRepository.getBiometricKeyAlias().isNullOrEmpty()
                
                updateUiState(
                    biometricAvailable = isAvailable,
                    biometricSetup = hasExistingBiometric
                )
                
                if (!isAvailable) {
                    Timber.w("Biometric not available: $availability")
                }
            } catch (e: Exception) {
                Timber.e(e, "Failed to check biometric availability")
                updateUiState(biometricAvailable = false)
            }
        }
    }
    
    /**
     * Setup biometric authentication
     */
    fun setupBiometric(activity: FragmentActivity) {
        viewModelScope.launch {
            try {
                val currentUser = authRepository.currentUser.first()
                if (currentUser == null) {
                    updateUiState(error = "User not logged in")
                    return@launch
                }
                
                updateUiState(isLoading = true, error = null)
                
                secureBiometricManager.setupBiometricAuth(
                    activity = activity,
                    userId = currentUser.id,
                    onSuccess = { keyAlias ->
                        viewModelScope.launch {
                            try {
                                authRepository.setBiometricEnabled(true)
                                authRepository.saveBiometricKeyAlias(keyAlias)
                                updateUiState(
                                    isLoading = false,
                                    biometricSetup = true,
                                    message = "Biometric authentication enabled successfully"
                                )
                                Timber.i("Biometric setup completed for user: ${currentUser.id}")
                            } catch (e: Exception) {
                                Timber.e(e, "Failed to save biometric setup")
                                updateUiState(
                                    isLoading = false,
                                    error = "Failed to save biometric setup"
                                )
                            }
                        }
                    },
                    onError = { error ->
                        updateUiState(
                            isLoading = false,
                            error = "Biometric setup failed: $error"
                        )
                    }
                )
            } catch (e: Exception) {
                Timber.e(e, "Biometric setup error")
                updateUiState(
                    isLoading = false,
                    error = "Failed to setup biometric authentication"
                )
            }
        }
    }
    
    /**
     * Authenticate with biometric
     */
    fun authenticateWithBiometric(activity: FragmentActivity) {
        viewModelScope.launch {
            try {
                val keyAlias = authRepository.getBiometricKeyAlias()
                if (keyAlias.isNullOrEmpty()) {
                    updateUiState(error = "Biometric not set up")
                    return@launch
                }
                
                updateUiState(isLoading = true, error = null)
                
                secureBiometricManager.authenticateWithBiometric(
                    activity = activity,
                    keyAlias = keyAlias,
                    title = "PLS Travels Login",
                    subtitle = "Use biometric to access your account",
                    description = "Authenticate to access PLS Travels Driver app",
                    onSuccess = { encryptedData ->
                        viewModelScope.launch {
                            try {
                                // Validate current session
                                val sessionResult = authRepository.validateAndRefreshSession()
                                sessionResult.fold(
                                    onSuccess = { isValid ->
                                        if (isValid) {
                                            updateUiState(
                                                isLoading = false,
                                                loginSuccessful = true,
                                                message = "Biometric login successful"
                                            )
                                            Timber.i("Biometric authentication successful")
                                        } else {
                                            updateUiState(
                                                isLoading = false,
                                                error = "Session expired. Please login with phone number."
                                            )
                                        }
                                    },
                                    onFailure = { exception ->
                                        Timber.e(exception, "Session validation failed")
                                        updateUiState(
                                            isLoading = false,
                                            error = "Session validation failed. Please login again."
                                        )
                                    }
                                )
                            } catch (e: Exception) {
                                Timber.e(e, "Biometric authentication processing failed")
                                updateUiState(
                                    isLoading = false,
                                    error = "Authentication processing failed"
                                )
                            }
                        }
                    },
                    onError = { error ->
                        updateUiState(
                            isLoading = false,
                            error = "Biometric authentication failed: $error"
                        )
                    },
                    onFailed = {
                        updateUiState(
                            isLoading = false,
                            error = null // Don't show error for user cancellation
                        )
                    }
                )
            } catch (e: Exception) {
                Timber.e(e, "Biometric authentication error")
                updateUiState(
                    isLoading = false,
                    error = "Biometric authentication not available"
                )
            }
        }
    }
    
    /**
     * Disable biometric authentication
     */
    fun disableBiometric() {
        viewModelScope.launch {
            try {
                val keyAlias = authRepository.getBiometricKeyAlias()
                if (!keyAlias.isNullOrEmpty()) {
                    secureBiometricManager.disableBiometricAuth(keyAlias)
                }
                
                authRepository.setBiometricEnabled(false)
                authRepository.saveBiometricKeyAlias(null)
                
                updateUiState(
                    biometricSetup = false,
                    message = "Biometric authentication disabled"
                )
                
                Timber.i("Biometric authentication disabled")
            } catch (e: Exception) {
                Timber.e(e, "Failed to disable biometric")
                updateUiState(error = "Failed to disable biometric authentication")
            }
        }
    }
    
    /**
     * Validate current session on app start
     */
    fun validateSession() {
        viewModelScope.launch {
            try {
                val sessionResult = authRepository.validateAndRefreshSession()
                sessionResult.fold(
                    onSuccess = { isValid ->
                        if (isValid) {
                            updateUiState(loginSuccessful = true)
                            Timber.i("Session validated successfully")
                        } else {
                            Timber.i("Session invalid, user needs to login")
                        }
                    },
                    onFailure = { exception ->
                        Timber.e(exception, "Session validation failed")
                    }
                )
            } catch (e: Exception) {
                Timber.e(e, "Session validation error")
            }
        }
    }

    private fun updateUiState(
        isLoading: Boolean? = null,
        otpSent: Boolean? = null,
        loginSuccessful: Boolean? = null,
        currentPhone: String? = null,
        error: String? = null,
        message: String? = null,
        biometricAvailable: Boolean? = null,
        biometricSetup: Boolean? = null
    ) {
        uiState = uiState.copy(
            isLoading = isLoading ?: uiState.isLoading,
            otpSent = otpSent ?: uiState.otpSent,
            loginSuccessful = loginSuccessful ?: uiState.loginSuccessful,
            currentPhone = currentPhone ?: uiState.currentPhone,
            error = error,
            message = message,
            biometricAvailable = biometricAvailable ?: uiState.biometricAvailable,
            biometricSetup = biometricSetup ?: uiState.biometricSetup
        )
    }
}

/**
 * UI state for authentication screens
 */
data class AuthUiState(
    val isLoading: Boolean = false,
    val otpSent: Boolean = false,
    val loginSuccessful: Boolean = false,
    val currentPhone: String = "",
    val error: String? = null,
    val message: String? = null,
    val biometricAvailable: Boolean = false,
    val biometricSetup: Boolean = false
)