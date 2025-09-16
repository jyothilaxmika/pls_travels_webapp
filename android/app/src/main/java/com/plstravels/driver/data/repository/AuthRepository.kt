package com.plstravels.driver.data.repository

import com.plstravels.driver.data.local.TokenManager
import com.plstravels.driver.data.models.*
import com.plstravels.driver.data.network.ApiService
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject
import javax.inject.Singleton
import android.provider.Settings
import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext

/**
 * Repository for authentication operations
 * Handles OTP flow and token management
 */
@Singleton
class AuthRepository @Inject constructor(
    private val apiService: ApiService,
    private val tokenManager: TokenManager,
    @ApplicationContext private val context: Context
) {
    
    val isLoggedIn: Flow<Boolean> = tokenManager.isLoggedIn
    
    suspend fun sendOtp(phoneNumber: String): Result<SendOtpResponse> {
        return try {
            val formattedPhone = formatPhoneNumber(phoneNumber)
            val request = SendOtpRequest(phoneNumber = formattedPhone)
            val response = apiService.sendOtp(request)
            
            if (response.isSuccessful && response.body()?.success == true) {
                Result.success(response.body()!!)
            } else {
                val errorMessage = response.body()?.message 
                    ?: "Failed to send OTP. Please try again."
                Result.failure(Exception(errorMessage))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun verifyOtp(phoneNumber: String, otpCode: String): Result<VerifyOtpResponse> {
        return try {
            val formattedPhone = formatPhoneNumber(phoneNumber)
            val deviceId = getDeviceId()
            val request = VerifyOtpRequest(
                phoneNumber = formattedPhone,
                otpCode = otpCode,
                deviceId = deviceId
            )
            
            val response = apiService.verifyOtp(request)
            
            if (response.isSuccessful && response.body()?.success == true) {
                val body = response.body()!!
                
                // Save tokens and user info
                if (body.accessToken != null && body.refreshToken != null && body.user != null) {
                    tokenManager.saveTokens(
                        accessToken = body.accessToken,
                        refreshToken = body.refreshToken,
                        userId = body.user.id,
                        username = body.user.username,
                        role = body.user.role,
                        expiresIn = body.tokenExpiresIn ?: 3600
                    )
                }
                
                Result.success(body)
            } else {
                val errorMessage = response.body()?.message 
                    ?: "Invalid OTP. Please try again."
                Result.failure(Exception(errorMessage))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun refreshToken(): Result<RefreshTokenResponse> {
        return try {
            val refreshToken = tokenManager.getRefreshToken()
            if (refreshToken.isNullOrEmpty()) {
                tokenManager.clearTokens()
                return Result.failure(Exception("No refresh token available"))
            }
            
            val request = RefreshTokenRequest(refreshToken = refreshToken)
            val response = apiService.refreshToken(request)
            
            if (response.isSuccessful && response.body()?.success == true) {
                val body = response.body()!!
                
                // Update access token
                if (body.accessToken != null) {
                    tokenManager.updateAccessToken(
                        accessToken = body.accessToken,
                        expiresIn = body.expiresIn ?: 3600
                    )
                }
                
                Result.success(body)
            } else {
                // Refresh failed, clear tokens
                tokenManager.clearTokens()
                Result.failure(Exception("Session expired. Please login again."))
            }
        } catch (e: Exception) {
            tokenManager.clearTokens()
            Result.failure(e)
        }
    }
    
    suspend fun logout(): Result<Unit> {
        return try {
            // Call logout endpoint to blacklist tokens
            apiService.logout()
            
            // Clear local tokens regardless of API response
            tokenManager.clearTokens()
            
            Result.success(Unit)
        } catch (e: Exception) {
            // Clear tokens even if API call fails
            tokenManager.clearTokens()
            Result.success(Unit)
        }
    }
    
    suspend fun getCurrentUserId(): Int {
        return tokenManager.getCurrentUserId()
    }
    
    suspend fun getCurrentUsername(): String? {
        return tokenManager.getCurrentUsername()
    }
    
    suspend fun getCurrentUserRole(): String? {
        return tokenManager.getCurrentUserRole()
    }
    
    private fun formatPhoneNumber(phoneNumber: String): String {
        // Remove all non-digit characters
        val cleanPhone = phoneNumber.replace(Regex("[^\\d]"), "")
        
        // Add +91 prefix if not present
        return when {
            cleanPhone.startsWith("91") && cleanPhone.length == 12 -> "+$cleanPhone"
            cleanPhone.length == 10 -> "+91$cleanPhone"
            else -> "+91$cleanPhone" // Fallback, may need validation
        }
    }
    
    private fun getDeviceId(): String {
        return try {
            Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
        } catch (e: Exception) {
            "unknown_device"
        }
    }
}