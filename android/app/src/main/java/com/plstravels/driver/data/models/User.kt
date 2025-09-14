package com.plstravels.driver.data.models

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.google.gson.annotations.SerializedName

/**
 * User data model for driver authentication and profile
 */
@Entity(tableName = "users")
data class User(
    @PrimaryKey
    val id: Int,
    val username: String,
    @SerializedName("full_name")
    val fullName: String,
    val phone: String,
    val email: String?,
    val role: String,
    @SerializedName("branch_name")
    val branchName: String?
)

/**
 * Authentication request models
 */
data class SendOtpRequest(
    @SerializedName("phone_number")
    val phoneNumber: String
)

data class VerifyOtpRequest(
    @SerializedName("phone_number")
    val phoneNumber: String,
    @SerializedName("otp_code")
    val otpCode: String,
    @SerializedName("device_id")
    val deviceId: String? = null
)

/**
 * Authentication response models
 */
data class SendOtpResponse(
    val success: Boolean,
    val message: String,
    @SerializedName("session_id")
    val sessionId: String? = null,
    @SerializedName("retry_after")
    val retryAfter: Int? = null
)

data class VerifyOtpResponse(
    val success: Boolean,
    val message: String,
    @SerializedName("access_token")
    val accessToken: String? = null,
    @SerializedName("refresh_token")
    val refreshToken: String? = null,
    val user: User? = null,
    @SerializedName("token_expires_in")
    val tokenExpiresIn: Int? = null
)

data class RefreshTokenResponse(
    val success: Boolean,
    @SerializedName("access_token")
    val accessToken: String? = null,
    @SerializedName("token_expires_in")
    val tokenExpiresIn: Int? = null,
    val error: String? = null,
    val message: String? = null
)