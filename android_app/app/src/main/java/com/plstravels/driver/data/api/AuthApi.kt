package com.plstravels.driver.data.api

import com.plstravels.driver.data.model.AuthResponse
import com.plstravels.driver.data.model.OtpSendResponse
import retrofit2.Response
import retrofit2.http.Field
import retrofit2.http.FormUrlEncoded
import retrofit2.http.POST

/**
 * Authentication API interface for mobile app
 */
interface AuthApi {

    @POST("/auth/send-otp")
    @FormUrlEncoded
    suspend fun sendOtp(
        @Field("phone") phone: String
    ): Response<OtpSendResponse>

    @POST("/auth/verify-otp")
    @FormUrlEncoded
    suspend fun verifyOtp(
        @Field("phone") phone: String,
        @Field("otp") otp: String,
        @Field("device_info") deviceInfo: String? = null,
        @Field("fcm_token") fcmToken: String? = null
    ): Response<AuthResponse>

    @POST("/auth/refresh")
    @FormUrlEncoded
    suspend fun refreshToken(
        @Field("refresh_token") refreshToken: String
    ): Response<AuthResponse>

    @POST("/auth/logout")
    suspend fun logout(): Response<ApiResponse<Any>>
    
    @POST("/auth/update-fcm-token")
    @FormUrlEncoded
    suspend fun updateFcmToken(
        @Field("fcm_token") fcmToken: String
    ): Response<ApiResponse<String>>
}

/**
 * Generic API response wrapper
 */
data class ApiResponse<T>(
    val success: Boolean,
    val data: T?,
    val message: String?,
    val error: String?
)