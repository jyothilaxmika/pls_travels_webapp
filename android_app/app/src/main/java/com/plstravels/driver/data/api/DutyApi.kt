package com.plstravels.driver.data.api

import com.plstravels.driver.data.model.*
import okhttp3.MultipartBody
import retrofit2.Response
import retrofit2.http.*

/**
 * Duty management API interface
 */
interface DutyApi {

    @GET("/driver/profile")
    suspend fun getDriverProfile(): Response<ApiResponse<User>>

    @GET("/driver/duties")
    suspend fun getDuties(
        @Query("page") page: Int = 1,
        @Query("per_page") perPage: Int = 20,
        @Query("status") status: String? = null
    ): Response<ApiResponse<List<Duty>>>

    @GET("/driver/vehicles")
    suspend fun getAvailableVehicles(): Response<ApiResponse<List<Vehicle>>>

    @POST("/driver/duty/start")
    suspend fun startDuty(
        @Body request: DutyStartRequest
    ): Response<ApiResponse<Duty>>

    @POST("/driver/duty/end")
    suspend fun endDuty(
        @Body request: DutyEndRequest
    ): Response<ApiResponse<Duty>>

    @Multipart
    @POST("/driver/upload-photo")
    suspend fun uploadPhoto(
        @Part photo: MultipartBody.Part,
        @Part("duty_phase") dutyPhase: String? = null
    ): Response<PhotoUploadResponse>

    @POST("/driver/location/update")
    suspend fun updateLocation(
        @Body request: LocationUpdateRequest
    ): Response<ApiResponse<Any>>

    @POST("/driver/fcm-token")
    suspend fun registerFcmToken(
        @Body request: FcmTokenRequest
    ): Response<ApiResponse<Any>>

    @POST("/driver/advance-payment")
    suspend fun requestAdvancePayment(
        @Body request: AdvancePaymentRequest
    ): Response<ApiResponse<AdvancePaymentResponse>>

    @GET("/driver/advance-payments")
    suspend fun getAdvancePayments(
        @Query("page") page: Int = 1,
        @Query("per_page") perPage: Int = 20,
        @Query("status") status: String? = null
    ): Response<ApiResponse<List<AdvancePayment>>>

    @GET("/health")
    suspend fun healthCheck(): Response<ApiResponse<Any>>
}

/**
 * Photo upload response
 */
data class PhotoUploadResponse(
    val success: Boolean,
    val file_url: String?,
    val filename: String?,
    val message: String?,
    val error: String?
)

/**
 * Location update request
 */
data class LocationUpdateRequest(
    val latitude: Double,
    val longitude: Double,
    val accuracy: Float = 0f,
    val speed: Float = 0f,
    val heading: Float = 0f,
    val device_info: Map<String, Any>? = null
)

/**
 * FCM token registration request
 */
data class FcmTokenRequest(
    val fcm_token: String
)

/**
 * Advance payment request
 */
data class AdvancePaymentRequest(
    val amount: Double,
    val purpose: String,
    val notes: String? = null,
    val latitude: Double? = null,
    val longitude: Double? = null
)

/**
 * Advance payment response
 */
data class AdvancePaymentResponse(
    val request_id: String,
    val message: String,
    val sent_to_admins: Int
)

/**
 * Advance payment history item
 */
data class AdvancePayment(
    val id: String,
    val amount_requested: Double,
    val amount_approved: Double?,
    val purpose: String,
    val notes: String?,
    val status: String,
    val created_at: String,
    val responded_at: String?,
    val response_notes: String?,
    val duty_id: Int
)