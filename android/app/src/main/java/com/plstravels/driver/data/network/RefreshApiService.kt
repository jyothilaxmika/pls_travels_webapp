package com.plstravels.driver.data.network

import com.plstravels.driver.data.models.RefreshTokenRequest
import com.plstravels.driver.data.models.RefreshTokenResponse
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.POST

/**
 * Dedicated API service for token refresh operations
 * This service doesn't use the AuthInterceptor to avoid circular dependency
 */
interface RefreshApiService {
    
    @POST("api/v1/auth/refresh")
    suspend fun refreshToken(@Body request: RefreshTokenRequest): Response<RefreshTokenResponse>
}