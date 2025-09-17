package com.plstravels.driver.data.repository

import android.content.Context
import com.plstravels.driver.data.api.AuthApi
import com.plstravels.driver.data.model.AuthResponse
import com.plstravels.driver.data.model.OtpSendResponse
import com.plstravels.driver.data.storage.SecureStorageManager
import com.plstravels.driver.security.SecurityManager
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOf
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Repository for authentication and token management
 */
@Singleton
class AuthRepository @Inject constructor(
    @ApplicationContext private val context: Context,
    private val authApi: AuthApi,
    private val secureStorage: SecureStorageManager,
    private val securityManager: SecurityManager
) {


    /**
     * Check if user is currently logged in
     */
    val isLoggedIn: Flow<Boolean> = flow {
        try {
            val isLoggedIn = secureStorage.getBoolean(SecureStorageManager.KEY_IS_LOGGED_IN, false)
            emit(isLoggedIn)
        } catch (e: Exception) {
            Timber.e(e, "Failed to get login status")
            emit(false)
        }
    }

    /**
     * Get current access token
     */
    val accessToken: Flow<String?> = flow {
        try {
            val token = secureStorage.getString(SecureStorageManager.KEY_ACCESS_TOKEN)
            emit(token)
        } catch (e: Exception) {
            Timber.e(e, "Failed to get access token")
            emit(null)
        }
    }

    /**
     * Get current user info
     */
    val currentUser: Flow<UserInfo?> = flow {
        try {
            val userId = secureStorage.getInt(SecureStorageManager.KEY_USER_ID, 0)
            val username = secureStorage.getString(SecureStorageManager.KEY_USERNAME)
            val fullName = secureStorage.getString(SecureStorageManager.KEY_FULL_NAME)
            val phone = secureStorage.getString(SecureStorageManager.KEY_PHONE)
            
            if (userId > 0 && !username.isNullOrEmpty() && !fullName.isNullOrEmpty() && !phone.isNullOrEmpty()) {
                emit(UserInfo(userId, username, fullName, phone))
            } else {
                emit(null)
            }
        } catch (e: Exception) {
            Timber.e(e, "Failed to get current user")
            emit(null)
        }
    }

    /**
     * Send OTP to phone number with security validation
     */
    suspend fun sendOtp(phone: String): Result<OtpSendResponse> {
        return try {
            // Perform security check before sensitive operations
            val securityCheck = securityManager.performSecurityCheck()
            if (securityCheck.shouldBlockAccess) {
                Timber.e("Security check failed, blocking OTP request: ${securityCheck.violations}")
                return Result.failure(SecurityException("Security validation failed. Please ensure your device is secure."))
            }
            
            if (!securityCheck.isSecure) {
                Timber.w("Security warnings detected: ${securityCheck.violations}")
            }
            
            val response = authApi.sendOtp(phone)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                val errorMessage = response.errorBody()?.string() ?: "Failed to send OTP"
                Timber.e("Send OTP failed: $errorMessage")
                Result.failure(Exception(errorMessage))
            }
        } catch (e: SecurityException) {
            Timber.e(e, "Security exception during OTP send")
            Result.failure(e)
        } catch (e: Exception) {
            Timber.e(e, "Send OTP exception")
            Result.failure(e)
        }
    }

    /**
     * Verify OTP and login with enhanced security
     */
    suspend fun verifyOtp(
        phone: String, 
        otp: String, 
        deviceInfo: String? = null, 
        fcmToken: String? = null
    ): Result<AuthResponse> {
        return try {
            // Enhanced security check for login
            val securityCheck = securityManager.performSecurityCheck()
            if (securityCheck.shouldBlockAccess) {
                Timber.e("Security check failed, blocking login: ${securityCheck.violations}")
                return Result.failure(SecurityException("Login blocked due to security concerns. ${securityManager.getSecurityRecommendations(securityCheck.violations).joinToString("; ")}"))
            }
            
            val response = authApi.verifyOtp(phone, otp, deviceInfo, fcmToken)
            if (response.isSuccessful && response.body() != null) {
                val authResponse = response.body()!!
                if (authResponse.success) {
                    // Save tokens and user info securely
                    saveAuthData(authResponse)
                    
                    // Reset security violation count on successful login
                    securityManager.resetSecurityViolationCount()
                    
                    // Sync FCM token after successful login
                    try {
                        syncCurrentFcmToken().fold(
                            onSuccess = {
                                Timber.i("FCM token synced successfully after login")
                            },
                            onFailure = { exception ->
                                Timber.w(exception, "Failed to sync FCM token after login (non-critical)")
                            }
                        )
                    } catch (e: Exception) {
                        Timber.w(e, "Exception during FCM token sync after login (non-critical)")
                    }
                    
                    Timber.i("User authenticated successfully with enhanced security")
                }
                Result.success(authResponse)
            } else {
                val errorMessage = response.errorBody()?.string() ?: "Failed to verify OTP"
                Timber.e("Verify OTP failed: $errorMessage")
                Result.failure(Exception(errorMessage))
            }
        } catch (e: SecurityException) {
            Timber.e(e, "Security exception during OTP verification")
            Result.failure(e)
        } catch (e: Exception) {
            Timber.e(e, "Verify OTP exception")
            Result.failure(e)
        }
    }

    /**
     * Refresh access token
     */
    suspend fun refreshToken(): Result<AuthResponse> {
        return try {
            val refreshToken = getRefreshToken()
            if (refreshToken == null) {
                return Result.failure(Exception("No refresh token available"))
            }

            val response = authApi.refreshToken(refreshToken)
            if (response.isSuccessful && response.body() != null) {
                val authResponse = response.body()!!
                if (authResponse.success) {
                    // Save new tokens
                    saveAuthData(authResponse)
                }
                Result.success(authResponse)
            } else {
                val errorMessage = response.errorBody()?.string() ?: "Failed to refresh token"
                Timber.e("Refresh token failed: $errorMessage")
                Result.failure(Exception(errorMessage))
            }
        } catch (e: Exception) {
            Timber.e(e, "Refresh token exception")
            Result.failure(e)
        }
    }

    /**
     * Logout user
     */
    suspend fun logout(): Result<Unit> {
        return try {
            // Call logout API
            authApi.logout()
            
            // Clear all stored data
            clearAuthData()
            Timber.i("User logged out successfully")
            
            Result.success(Unit)
        } catch (e: Exception) {
            Timber.e(e, "Logout exception")
            // Clear local data even if API call fails
            clearAuthData()
            Result.success(Unit)
        }
    }

    /**
     * Get current access token synchronously (for interceptors)
     */
    suspend fun getCurrentAccessToken(): String? {
        return try {
            secureStorage.getString(SecureStorageManager.KEY_ACCESS_TOKEN)
        } catch (e: Exception) {
            Timber.e(e, "Failed to get access token")
            null
        }
    }
    
    /**
     * Update FCM token on server
     */
    suspend fun updateFcmToken(fcmToken: String): Result<String> {
        return try {
            val response = authApi.updateFcmToken(fcmToken)
            if (response.isSuccessful && response.body() != null) {
                val apiResponse = response.body()!!
                if (apiResponse.success) {
                    Timber.i("FCM token updated successfully on server")
                    Result.success(apiResponse.data ?: "Token updated")
                } else {
                    val errorMessage = apiResponse.error ?: "Failed to update FCM token"
                    Timber.e("Update FCM token failed: $errorMessage")
                    Result.failure(Exception(errorMessage))
                }
            } else {
                val errorMessage = response.errorBody()?.string() ?: "Failed to update FCM token"
                Timber.e("Update FCM token API failed: $errorMessage")
                Result.failure(Exception(errorMessage))
            }
        } catch (e: Exception) {
            Timber.e(e, "Update FCM token exception")
            Result.failure(e)
        }
    }

    /**
     * Sync current FCM token with server after login or app start
     * This method retrieves the current FCM token and sends it to the server
     */
    suspend fun syncCurrentFcmToken(): Result<String> {
        return try {
            // Get the current FCM token
            val task = com.google.firebase.messaging.FirebaseMessaging.getInstance().token
            val fcmToken = kotlinx.coroutines.tasks.await(task)
            
            if (fcmToken.isNotEmpty()) {
                Timber.d("Retrieved current FCM token for sync: ${fcmToken.take(20)}...")
                updateFcmToken(fcmToken)
            } else {
                val errorMessage = "FCM token is empty"
                Timber.w(errorMessage)
                Result.failure(Exception(errorMessage))
            }
        } catch (e: Exception) {
            Timber.e(e, "Failed to sync current FCM token")
            Result.failure(e)
        }
    }

    private suspend fun getRefreshToken(): String? {
        return try {
            secureStorage.getString(SecureStorageManager.KEY_REFRESH_TOKEN)
        } catch (e: Exception) {
            Timber.e(e, "Failed to get refresh token")
            null
        }
    }

    private suspend fun saveAuthData(authResponse: AuthResponse) {
        try {
            authResponse.accessToken?.let {
                secureStorage.saveString(SecureStorageManager.KEY_ACCESS_TOKEN, it)
            }
            authResponse.refreshToken?.let {
                secureStorage.saveString(SecureStorageManager.KEY_REFRESH_TOKEN, it)
            }
            authResponse.expiresIn?.let {
                secureStorage.saveLong(SecureStorageManager.KEY_TOKEN_EXPIRES_AT, System.currentTimeMillis() + (it * 1000))
            }
            authResponse.user?.let { user ->
                secureStorage.saveInt(SecureStorageManager.KEY_USER_ID, user.id)
                secureStorage.saveString(SecureStorageManager.KEY_USERNAME, user.username)
                secureStorage.saveString(SecureStorageManager.KEY_FULL_NAME, user.fullName)
                secureStorage.saveString(SecureStorageManager.KEY_PHONE, user.phone)
            }
            secureStorage.saveBoolean(SecureStorageManager.KEY_IS_LOGGED_IN, true)
            secureStorage.saveLong(SecureStorageManager.KEY_LAST_LOGIN_TIME, System.currentTimeMillis())
            
            Timber.i("Auth data saved securely")
        } catch (e: Exception) {
            Timber.e(e, "Failed to save auth data securely")
            throw SecurityException("Failed to save authentication data", e)
        }
    }

    private suspend fun clearAuthData() {
        try {
            secureStorage.clearAll()
            Timber.i("Auth data cleared securely")
        } catch (e: Exception) {
            Timber.e(e, "Failed to clear auth data")
        }
    }

    /**
     * Enable/disable biometric authentication
     */
    suspend fun setBiometricEnabled(enabled: Boolean) {
        try {
            secureStorage.saveBoolean(SecureStorageManager.KEY_BIOMETRIC_ENABLED, enabled)
            Timber.i("Biometric setting updated: $enabled")
        } catch (e: Exception) {
            Timber.e(e, "Failed to update biometric setting")
        }
    }

    /**
     * Check if biometric authentication is enabled
     */
    val isBiometricEnabled: Flow<Boolean> = flow {
        try {
            val enabled = secureStorage.getBoolean(SecureStorageManager.KEY_BIOMETRIC_ENABLED, false)
            emit(enabled)
        } catch (e: Exception) {
            Timber.e(e, "Failed to get biometric setting")
            emit(false)
        }
    }

    /**
     * Check if current token is valid (not expired)
     */
    suspend fun isTokenValid(): Boolean {
        return try {
            val expiresAt = secureStorage.getLong(SecureStorageManager.KEY_TOKEN_EXPIRES_AT, 0L)
            val currentTime = System.currentTimeMillis()
            val isValid = expiresAt > currentTime + (5 * 60 * 1000) // 5 minute buffer
            
            if (!isValid) {
                Timber.w("Token expired or expiring soon")
            }
            
            isValid
        } catch (e: Exception) {
            Timber.e(e, "Failed to check token validity")
            false
        }
    }

    /**
     * Get time until token expires (in milliseconds)
     */
    suspend fun getTimeUntilExpiry(): Long {
        return try {
            val expiresAt = secureStorage.getLong(SecureStorageManager.KEY_TOKEN_EXPIRES_AT, 0L)
            val currentTime = System.currentTimeMillis()
            maxOf(0L, expiresAt - currentTime)
        } catch (e: Exception) {
            Timber.e(e, "Failed to get token expiry time")
            0L
        }
    }

    /**
     * Save biometric key alias for secure biometric authentication
     */
    suspend fun saveBiometricKeyAlias(keyAlias: String) {
        try {
            secureStorage.saveString(SecureStorageManager.KEY_BIOMETRIC_KEY_ALIAS, keyAlias)
            Timber.i("Biometric key alias saved securely")
        } catch (e: Exception) {
            Timber.e(e, "Failed to save biometric key alias")
        }
    }

    /**
     * Get biometric key alias
     */
    suspend fun getBiometricKeyAlias(): String? {
        return try {
            secureStorage.getString(SecureStorageManager.KEY_BIOMETRIC_KEY_ALIAS)
        } catch (e: Exception) {
            Timber.e(e, "Failed to get biometric key alias")
            null
        }
    }

    /**
     * Validate session health and auto-refresh if needed
     */
    suspend fun validateAndRefreshSession(): Result<Boolean> {
        return try {
            val isLoggedIn = secureStorage.getBoolean(SecureStorageManager.KEY_IS_LOGGED_IN, false)
            
            if (!isLoggedIn) {
                return Result.success(false)
            }

            // Check if token is still valid
            if (isTokenValid()) {
                return Result.success(true)
            }

            // Try to refresh token
            val refreshResult = refreshToken()
            refreshResult.fold(
                onSuccess = { authResponse ->
                    if (authResponse.success) {
                        Timber.i("Session refreshed successfully")
                        Result.success(true)
                    } else {
                        Timber.w("Session refresh failed: ${authResponse.error}")
                        Result.success(false)
                    }
                },
                onFailure = { exception ->
                    Timber.e(exception, "Session refresh failed")
                    // Clear invalid session data
                    clearAuthData()
                    Result.success(false)
                }
            )
        } catch (e: Exception) {
            Timber.e(e, "Failed to validate session")
            Result.failure(e)
        }
    }

    data class UserInfo(
        val id: Int,
        val username: String,
        val fullName: String,
        val phone: String
    )

    /**
     * Comprehensive security health check for the repository
     */
    suspend fun performSecurityHealthCheck(): SecurityHealthStatus {
        return try {
            // Check storage health
            val storageHealthy = secureStorage.isStorageHealthy()
            val hasValidSession = secureStorage.getBoolean(SecureStorageManager.KEY_IS_LOGGED_IN, false)
            val tokenValid = if (hasValidSession) isTokenValid() else true
            
            // Perform system security check
            val systemSecurityCheck = securityManager.performSecurityCheck()
            
            SecurityHealthStatus(
                storageHealthy = storageHealthy,
                sessionValid = hasValidSession && tokenValid,
                biometricConfigured = secureStorage.getBoolean(SecureStorageManager.KEY_BIOMETRIC_ENABLED, false),
                systemSecure = systemSecurityCheck.isSecure,
                securityViolations = systemSecurityCheck.violations,
                securityLevel = systemSecurityCheck.severityLevel,
                shouldBlockAccess = systemSecurityCheck.shouldBlockAccess,
                securityRecommendations = securityManager.getSecurityRecommendations(systemSecurityCheck.violations)
            )
        } catch (e: Exception) {
            Timber.e(e, "Security health check failed")
            SecurityHealthStatus(
                storageHealthy = false,
                sessionValid = false,
                biometricConfigured = false,
                systemSecure = false,
                securityViolations = listOf(SecurityManager.SecurityViolation.SECURITY_CHECK_FAILED),
                securityLevel = SecurityManager.SecurityLevel.CRITICAL,
                shouldBlockAccess = true,
                securityRecommendations = listOf("Contact support - security system unavailable")
            )
        }
    }

    data class SecurityHealthStatus(
        val storageHealthy: Boolean,
        val sessionValid: Boolean,
        val biometricConfigured: Boolean,
        val systemSecure: Boolean,
        val securityViolations: List<SecurityManager.SecurityViolation>,
        val securityLevel: SecurityManager.SecurityLevel,
        val shouldBlockAccess: Boolean,
        val securityRecommendations: List<String>
    )
}