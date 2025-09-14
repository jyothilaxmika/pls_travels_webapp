package com.plstravels.driver.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.plstravels.driver.data.repository.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * ViewModel for authentication flow (OTP login)
 */
@HiltViewModel
class AuthViewModel @Inject constructor(
    private val authRepository: AuthRepository
) : ViewModel() {
    
    private val _uiState = MutableStateFlow(AuthUiState())
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()
    
    private val _isLoggedIn = MutableStateFlow(false)
    val isLoggedIn: StateFlow<Boolean> = _isLoggedIn.asStateFlow()
    
    init {
        // Check if user is already logged in
        viewModelScope.launch {
            authRepository.isLoggedIn.collect { loggedIn ->
                _isLoggedIn.value = loggedIn
            }
        }
    }
    
    fun sendOtp(phoneNumber: String) {
        if (!isValidPhoneNumber(phoneNumber)) {
            _uiState.value = _uiState.value.copy(
                error = "Please enter a valid phone number",
                isLoading = false
            )
            return
        }
        
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            
            try {
                val result = authRepository.sendOtp(phoneNumber)
                
                if (result.isSuccess) {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        otpSent = true,
                        phoneNumber = phoneNumber,
                        message = result.getOrNull()?.message ?: "OTP sent successfully"
                    )
                } else {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = result.exceptionOrNull()?.message ?: "Failed to send OTP"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message ?: "Network error occurred"
                )
            }
        }
    }
    
    fun verifyOtp(otpCode: String) {
        if (otpCode.length != 6) {
            _uiState.value = _uiState.value.copy(
                error = "Please enter a valid 6-digit OTP",
                isLoading = false
            )
            return
        }
        
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            
            try {
                val result = authRepository.verifyOtp(_uiState.value.phoneNumber, otpCode)
                
                if (result.isSuccess) {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        loginSuccess = true,
                        message = "Login successful"
                    )
                } else {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = result.exceptionOrNull()?.message ?: "Invalid OTP"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message ?: "Network error occurred"
                )
            }
        }
    }
    
    fun resendOtp() {
        if (_uiState.value.phoneNumber.isNotEmpty()) {
            sendOtp(_uiState.value.phoneNumber)
        }
    }
    
    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
    
    fun resetState() {
        _uiState.value = AuthUiState()
    }
    
    private fun isValidPhoneNumber(phone: String): Boolean {
        // Simple validation - should be 10 digits for Indian numbers
        val cleanPhone = phone.replace("+91", "").replace(" ", "").replace("-", "")
        return cleanPhone.length == 10 && cleanPhone.all { it.isDigit() }
    }
}

/**
 * UI state for authentication screen
 */
data class AuthUiState(
    val isLoading: Boolean = false,
    val otpSent: Boolean = false,
    val loginSuccess: Boolean = false,
    val phoneNumber: String = "",
    val message: String? = null,
    val error: String? = null
)