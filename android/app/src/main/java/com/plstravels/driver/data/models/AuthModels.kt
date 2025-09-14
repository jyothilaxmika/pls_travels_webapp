package com.plstravels.driver.data.models

import com.google.gson.annotations.SerializedName

/**
 * Authentication request/response models for OTP-based login
 */

// Send OTP Request
data class SendOtpRequest(
    @SerializedName("phone_number")
    val phoneNumber: String
)

data class SendOtpResponse(
    val success: Boolean,
    val message: String,
    @SerializedName("session_id")
    val sessionId: String? = null,
    val error: String? = null,
    @SerializedName("retry_after")
    val retryAfter: Int? = null
)

// Verify OTP Request
data class VerifyOtpRequest(
    @SerializedName("phone_number")
    val phoneNumber: String,
    @SerializedName("otp_code")
    val otpCode: String,
    @SerializedName("session_id")
    val sessionId: String? = null
)

data class VerifyOtpResponse(
    val success: Boolean,
    val message: String,
    @SerializedName("access_token")
    val accessToken: String? = null,
    @SerializedName("refresh_token")
    val refreshToken: String? = null,
    @SerializedName("token_type")
    val tokenType: String? = null,
    @SerializedName("expires_in")
    val expiresIn: Int? = null,
    val user: User? = null,
    val error: String? = null
)

// Refresh Token Request
data class RefreshTokenRequest(
    @SerializedName("refresh_token")
    val refreshToken: String
)

data class RefreshTokenResponse(
    val success: Boolean,
    val message: String,
    @SerializedName("access_token")
    val accessToken: String? = null,
    @SerializedName("refresh_token")
    val refreshToken: String? = null,
    @SerializedName("token_type")
    val tokenType: String? = null,
    @SerializedName("expires_in")
    val expiresIn: Int? = null,
    val error: String? = null
)

// FCM Token Management
data class FCMTokenRequest(
    @SerializedName("fcm_token")
    val fcmToken: String,
    @SerializedName("device_type")
    val deviceType: String = "android",
    @SerializedName("device_id")
    val deviceId: String? = null,
    @SerializedName("app_version")
    val appVersion: String? = null
)

data class FCMTokenResponse(
    val success: Boolean,
    val message: String,
    val error: String? = null
)

// Common response wrapper
data class DutiesResponse(
    val success: Boolean,
    val duties: List<Duty> = emptyList(),
    val pagination: PaginationInfo? = null,
    val error: String? = null
)

data class VehiclesResponse(
    val success: Boolean,
    val vehicles: List<Vehicle> = emptyList(),
    val error: String? = null
)

data class PaginationInfo(
    val page: Int,
    @SerializedName("per_page")
    val perPage: Int,
    val total: Int,
    @SerializedName("total_pages")
    val totalPages: Int
)

// Authentication state for local storage
data class AuthState(
    val isLoggedIn: Boolean = false,
    val accessToken: String? = null,
    val refreshToken: String? = null,
    val tokenType: String? = null,
    val expiresIn: Long? = null,
    val user: User? = null,
    val lastLoginTime: Long? = null
)

// Authentication errors
enum class AuthError(val code: String, val message: String) {
    NETWORK_ERROR("NETWORK_ERROR", "Network connection failed"),
    INVALID_PHONE("INVALID_PHONE", "Invalid phone number format"),
    INVALID_OTP("INVALID_OTP", "Invalid OTP code"),
    OTP_EXPIRED("OTP_EXPIRED", "OTP has expired"),
    TOO_MANY_ATTEMPTS("TOO_MANY_ATTEMPTS", "Too many attempts. Please try again later"),
    SERVICE_UNAVAILABLE("SERVICE_UNAVAILABLE", "Authentication service unavailable"),
    TOKEN_EXPIRED("TOKEN_EXPIRED", "Session has expired"),
    UNAUTHORIZED("UNAUTHORIZED", "Authentication required"),
    UNKNOWN_ERROR("UNKNOWN_ERROR", "An unexpected error occurred")
}

// Phone number validation
data class PhoneValidationResult(
    val isValid: Boolean,
    val formattedNumber: String? = null,
    val errorMessage: String? = null
)