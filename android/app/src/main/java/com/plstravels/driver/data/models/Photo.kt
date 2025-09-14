package com.plstravels.driver.data.models

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.google.gson.annotations.SerializedName

/**
 * Photo data models for duty documentation and vehicle inspections
 */
@Entity(tableName = "photos")
data class Photo(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val localFilePath: String,
    val fileName: String,
    val photoType: PhotoType,
    @SerializedName("duty_id")
    val dutyId: Int? = null,
    val timestamp: Long = System.currentTimeMillis(),
    val description: String? = null,
    
    // Upload status
    val isUploaded: Boolean = false,
    val uploadRetryCount: Int = 0,
    @SerializedName("server_url")
    val serverUrl: String? = null,
    val uploadError: String? = null
)

/**
 * Types of photos that can be captured
 */
enum class PhotoType(val displayName: String, val apiValue: String) {
    DUTY_START("Duty Start Photo", "duty_start"),
    DUTY_END("Duty End Photo", "duty_end"),
    VEHICLE_INSPECTION("Vehicle Inspection", "vehicle_inspection"),
    INCIDENT_REPORT("Incident Report", "incident"),
    ODOMETER_READING("Odometer Reading", "odometer"),
    FUEL_RECEIPT("Fuel Receipt", "fuel_receipt"),
    GENERAL("General Photo", "general")
}

/**
 * Photo capture request for API
 */
data class PhotoUploadRequest(
    val type: String,
    @SerializedName("duty_id")
    val dutyId: Int?,
    val description: String? = null
)

/**
 * Photo upload response from server
 */
data class PhotoUploadResponse(
    val success: Boolean,
    val message: String,
    @SerializedName("file_url")
    val fileUrl: String? = null,
    @SerializedName("photo_id")
    val photoId: String? = null,
    val error: String? = null
)

/**
 * Camera capture configuration
 */
data class CameraCaptureConfig(
    val targetResolution: CameraResolution = CameraResolution.MEDIUM,
    val jpegQuality: Int = 85,
    val enableFlash: Boolean = false,
    val enableGrid: Boolean = true,
    val maxFileSize: Long = 5 * 1024 * 1024 // 5MB
)

enum class CameraResolution(val width: Int, val height: Int) {
    LOW(640, 480),
    MEDIUM(1280, 720),
    HIGH(1920, 1080),
    FULL_HD(1920, 1080)
}