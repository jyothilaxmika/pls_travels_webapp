package com.plstravels.driver.data.network

import com.plstravels.driver.data.models.*
import retrofit2.Response
import retrofit2.http.*
import com.google.gson.annotations.SerializedName

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
    suspend fun refreshToken(@Body request: RefreshTokenRequest): Response<RefreshTokenResponse>
    
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
    
    // Location tracking endpoints - Updated for new GPS tracking system
    @POST("api/v1/tracking/locations/batch")
    suspend fun uploadLocationBatch(@Body request: LocationBatchRequest): Response<ApiResponse>
    
    @POST("api/v1/tracking/session/start")
    suspend fun startTrackingSession(@Body request: StartTrackingRequest): Response<TrackingSessionResponse>
    
    @POST("api/v1/tracking/session/end")
    suspend fun endTrackingSession(@Body request: EndTrackingRequest): Response<ApiResponse>
    
    // File upload endpoints
    @Multipart
    @POST("api/v1/driver/upload/photo")
    suspend fun uploadPhoto(
        @Part("type") type: String, // "duty_start", "duty_end", "incident"
        @Part("duty_id") dutyId: Int?,
        @Part file: okhttp3.MultipartBody.Part
    ): Response<FileUploadResponse>
    
    // FCM Push Notification endpoints
    @POST("api/v1/driver/fcm/token")
    suspend fun updateFCMToken(@Body request: FCMTokenRequest): Response<FCMTokenResponse>
    
    @POST("api/v1/driver/duty/{duty_id}/accept")
    suspend fun acceptDutyAssignment(@Path("duty_id") dutyId: Int): Response<ApiResponse>
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

// Updated location models to match backend GPS tracking system
data class LocationUpdate(
    val latitude: Double,
    val longitude: Double,
    val accuracy: Float,
    val altitude: Double? = null,
    val speed: Float? = null,
    val bearing: Float? = null,
    val timestamp: Long, // Unix timestamp in milliseconds
    @SerializedName("provider")
    val provider: String = "gps"
)

data class LocationBatchRequest(
    @SerializedName("locations")
    val locations: List<LocationUpdate>,
    @SerializedName("session_id")
    val sessionId: String? = null
)

data class StartTrackingRequest(
    @SerializedName("duty_id")
    val dutyId: Int,
    @SerializedName("vehicle_id") 
    val vehicleId: Int? = null
)

data class EndTrackingRequest(
    @SerializedName("session_id")
    val sessionId: String
)

data class TrackingSessionResponse(
    val success: Boolean,
    @SerializedName("session_id")
    val sessionId: String? = null,
    val message: String? = null,
    val error: String? = null
)

data class FileUploadResponse(
    val success: Boolean,
    val message: String,
    @SerializedName("file_url")
    val fileUrl: String? = null,
    val error: String? = null
)

// FCM Token models are defined in data.models package