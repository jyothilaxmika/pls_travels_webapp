package com.plstravels.driver.data.api.interceptor

import com.plstravels.driver.data.repository.AuthRepository
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton

/**
 * OkHttp interceptor that adds authentication headers to API requests
 */
@Singleton
class AuthInterceptor @Inject constructor(
    private val authRepository: AuthRepository
) : Interceptor {
    
    override fun intercept(chain: Interceptor.Chain): Response {
        val originalRequest = chain.request()
        
        // Skip authentication for auth endpoints
        if (originalRequest.url.encodedPath.contains("/auth/")) {
            return chain.proceed(originalRequest)
        }
        
        // Add access token to requests
        val accessToken = runBlocking { authRepository.getAccessToken() }
        
        return if (!accessToken.isNullOrEmpty()) {
            val authenticatedRequest = originalRequest.newBuilder()
                .header("Authorization", "Bearer $accessToken")
                .build()
            chain.proceed(authenticatedRequest)
        } else {
            chain.proceed(originalRequest)
        }
    }
}