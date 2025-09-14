package com.plstravels.driver.data.network

import com.plstravels.driver.data.models.*
import retrofit2.Response
import retrofit2.http.*

/**
 * Retrofit API service interface for PLS Travels mobile API
 */
interface ApiService {
    
    // Authentication endpoints
    @POST("api/v1/auth/send-otp")
    suspend fun sendOtp(@Body request: SendOtpRequest): Response<SendOtpResponse>
    
    @POST("api/v1/auth/verify-otp")
    suspend fun verifyOtp(@Body request: VerifyOtpRequest): Response<VerifyOtpResponse>
    
    @POST("api/v1/auth/refresh")
    suspend fun refreshToken(): Response<RefreshTokenResponse>
    
    @POST("api/v1/auth/logout")
    suspend fun logout(): Response<ApiResponse>
    
    // Driver profile endpoints
    @GET("api/v1/driver/profile")
    suspend fun getDriverProfile(): Response<DriverProfileResponse>
    
    // Duty management endpoints
    @GET("api/v1/driver/duties")
    suspend fun getDriverDuties(
        @Query("page") page: Int = 1,
        @Query("per_page") perPage: Int = 20,
        @Query("status") status: String? = null
    ): Response<DutiesResponse>
    
    @POST("api/v1/driver/duty/start")
    suspend fun startDuty(@Body request: StartDutyRequest): Response<DutyResponse>
    
    @POST("api/v1/driver/duty/end")
    suspend fun endDuty(@Body request: EndDutyRequest): Response<DutyResponse>
    
    // Vehicle endpoints
    @GET("api/v1/driver/vehicles")
    suspend fun getAvailableVehicles(): Response<VehiclesResponse>
    
    // Location tracking endpoints
    @POST("api/v1/driver/location")
    suspend fun uploadLocation(@Body locations: List<LocationUpdate>): Response<ApiResponse>
    
    // File upload endpoints
    @Multipart
    @POST("api/v1/driver/upload/photo")
    suspend fun uploadPhoto(
        @Part("type") type: String, // "duty_start", "duty_end", "incident"
        @Part("duty_id") dutyId: Int?,
        @Part file: okhttp3.MultipartBody.Part
    ): Response<FileUploadResponse>
}

/**
 * Common API response models
 */
data class ApiResponse(
    val success: Boolean,
    val message: String,
    val error: String? = null
)

data class DriverProfileResponse(
    val success: Boolean,
    val profile: User? = null,
    val error: String? = null
)

data class LocationUpdate(
    val latitude: Double,
    val longitude: Double,
    val accuracy: Float,
    val timestamp: Long,
    @SerializedName("duty_id")
    val dutyId: Int? = null
)

data class FileUploadResponse(
    val success: Boolean,
    val message: String,
    @SerializedName("file_url")
    val fileUrl: String? = null,
    val error: String? = null
)