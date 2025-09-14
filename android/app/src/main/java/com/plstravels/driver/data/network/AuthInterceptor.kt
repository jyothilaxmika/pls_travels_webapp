package com.plstravels.driver.data.network

import com.plstravels.driver.data.local.TokenManager
import kotlinx.coroutines.runBlocking
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
    private val tokenManager: TokenManager
) : Interceptor {
    
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
            
            // Try to refresh token
            val newToken = runBlocking { refreshTokenIfNeeded() }
            
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
    
    private suspend fun refreshTokenIfNeeded(): String? {
        val refreshToken = tokenManager.getRefreshToken()
        if (refreshToken.isNullOrEmpty()) {
            return null
        }
        
        return try {
            // This would typically call the refresh endpoint
            // For now, we'll just return null to trigger re-authentication
            tokenManager.clearTokens()
            null
        } catch (e: Exception) {
            tokenManager.clearTokens()
            null
        }
    }
}