package com.plstravels.driver.data.network

import com.plstravels.driver.data.local.TokenManager
import com.plstravels.driver.data.models.RefreshTokenRequest
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton

/**
 * OkHttp interceptor that automatically adds JWT tokens to API requests
 * and handles token refresh when needed
 */
@Singleton
class AuthInterceptor @Inject constructor(
    private val tokenManager: TokenManager,
    private val refreshApiService: RefreshApiService
) : Interceptor {
    
    // Mutex to prevent concurrent refresh attempts
    private val refreshMutex = Mutex()
    
    override fun intercept(chain: Interceptor.Chain): Response {
        val originalRequest = chain.request()
        
        // Skip auth for authentication endpoints
        if (originalRequest.url.encodedPath.contains("/auth/")) {
            return chain.proceed(originalRequest)
        }
        
        // Get current access token
        val accessToken = runBlocking { tokenManager.getAccessToken() }
        
        if (accessToken.isNullOrEmpty()) {
            return chain.proceed(originalRequest)
        }
        
        // Add Authorization header
        val authenticatedRequest = originalRequest.newBuilder()
            .header("Authorization", "Bearer $accessToken")
            .build()
        
        val response = chain.proceed(authenticatedRequest)
        
        // Handle 401 Unauthorized - token might be expired
        if (response.code == 401) {
            response.close()
            
            // Try to refresh token, passing the failed token to avoid returning the same one
            val newToken = runBlocking { refreshTokenIfNeeded(failedToken = accessToken) }
            
            if (newToken != null) {
                // Retry the request with new token
                val retryRequest = originalRequest.newBuilder()
                    .header("Authorization", "Bearer $newToken")
                    .build()
                
                return chain.proceed(retryRequest)
            }
        }
        
        return response
    }
    
    private suspend fun refreshTokenIfNeeded(failedToken: String?): String? {
        // Use mutex to prevent concurrent refresh attempts
        return refreshMutex.withLock {
            val refreshToken = tokenManager.getRefreshToken()
            if (refreshToken.isNullOrEmpty()) {
                return@withLock null
            }
            
            // Check if we already have a valid access token (another thread might have refreshed it)
            val currentAccessToken = tokenManager.getAccessToken()
            if (!currentAccessToken.isNullOrEmpty() && currentAccessToken != failedToken) {
                // We have a different token than the one that failed, return it
                return@withLock currentAccessToken
            }
            
            try {
                // Call the refresh endpoint using the separate refresh API service
                val refreshRequest = RefreshTokenRequest(refreshToken)
                val response = refreshApiService.refreshToken(refreshRequest)
                
                if (response.isSuccessful && response.body()?.success == true) {
                    val refreshResponse = response.body()!!
                    val newAccessToken = refreshResponse.accessToken
                    val newRefreshToken = refreshResponse.refreshToken
                    val expiresIn = refreshResponse.expiresIn ?: 3600 // Default to 1 hour
                    
                    if (!newAccessToken.isNullOrEmpty()) {
                        // Update tokens in storage
                        if (!newRefreshToken.isNullOrEmpty()) {
                            // If we got a new refresh token, update both
                            val userId = tokenManager.getCurrentUserId()
                            val username = tokenManager.getCurrentUsername() ?: ""
                            val role = tokenManager.getCurrentUserRole() ?: "driver"
                            
                            tokenManager.saveTokens(
                                accessToken = newAccessToken,
                                refreshToken = newRefreshToken,
                                userId = userId,
                                username = username,
                                role = role,
                                expiresIn = expiresIn
                            )
                        } else {
                            // Only update access token
                            tokenManager.updateAccessToken(newAccessToken, expiresIn)
                        }
                        
                        return@withLock newAccessToken
                    }
                }
                
                // Refresh failed, clear tokens to trigger re-authentication
                tokenManager.clearTokens()
                return@withLock null
                
            } catch (e: Exception) {
                // Network error or other exception during refresh
                // Clear tokens to trigger re-authentication
                tokenManager.clearTokens()
                return@withLock null
            }
        }
    }
}