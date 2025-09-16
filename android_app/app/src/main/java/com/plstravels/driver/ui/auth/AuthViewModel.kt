package com.plstravels.driver.ui.auth

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.plstravels.driver.data.repository.AuthRepository
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
    val authRepository: AuthRepository
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
     * Logout user
     */
    fun logout() {
        viewModelScope.launch {
            updateUiState(isLoading = true)
            
            try {
                authRepository.logout()
                updateUiState(
                    isLoading = false,
                    otpSent = false,
                    loginSuccessful = false,
                    currentPhone = "",
                    message = "Logged out successfully"
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

    private fun updateUiState(
        isLoading: Boolean? = null,
        otpSent: Boolean? = null,
        loginSuccessful: Boolean? = null,
        currentPhone: String? = null,
        error: String? = null,
        message: String? = null
    ) {
        uiState = uiState.copy(
            isLoading = isLoading ?: uiState.isLoading,
            otpSent = otpSent ?: uiState.otpSent,
            loginSuccessful = loginSuccessful ?: uiState.loginSuccessful,
            currentPhone = currentPhone ?: uiState.currentPhone,
            error = error,
            message = message
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
    val message: String? = null
)