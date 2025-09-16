package com.plstravels.driver.data.model

import com.google.gson.annotations.SerializedName

/**
 * User data model matching the backend API structure
 */
data class User(
    @SerializedName("id")
    val id: Int,
    
    @SerializedName("username")
    val username: String,
    
    @SerializedName("full_name")
    val fullName: String,
    
    @SerializedName("phone")
    val phone: String,
    
    @SerializedName("email")
    val email: String?,
    
    @SerializedName("branch")
    val branch: Branch?,
    
    @SerializedName("status")
    val status: String,
    
    @SerializedName("license_number")
    val licenseNumber: String?,
    
    @SerializedName("aadhar_number")
    val aadharNumber: String?,
    
    @SerializedName("address")
    val address: String?,
    
    @SerializedName("profile_photo_url")
    val profilePhotoUrl: String?
)

/**
 * Branch information
 */
data class Branch(
    @SerializedName("id")
    val id: Int,
    
    @SerializedName("name")
    val name: String
)

/**
 * Authentication response from API
 */
data class AuthResponse(
    @SerializedName("success")
    val success: Boolean,
    
    @SerializedName("access_token")
    val accessToken: String?,
    
    @SerializedName("refresh_token")
    val refreshToken: String?,
    
    @SerializedName("expires_in")
    val expiresIn: Long?,
    
    @SerializedName("user")
    val user: User?,
    
    @SerializedName("error")
    val error: String?,
    
    @SerializedName("message")
    val message: String?
)

/**
 * OTP send response
 */
data class OtpSendResponse(
    @SerializedName("success")
    val success: Boolean,
    
    @SerializedName("otp_sent")
    val otpSent: Boolean,
    
    @SerializedName("message")
    val message: String,
    
    @SerializedName("error")
    val error: String?,
    
    @SerializedName("retry_after")
    val retryAfter: Int?
)