package com.plstravels.driver.data.models

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.google.gson.annotations.SerializedName

/**
 * Location data models for tracking driver routes during duty
 */
@Entity(tableName = "location_points")
data class LocationPoint(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val latitude: Double,
    val longitude: Double,
    val accuracy: Float,
    val altitude: Double? = null,
    val bearing: Float? = null,
    val speed: Float? = null,
    val timestamp: Long,
    @SerializedName("duty_id")
    val dutyId: Int? = null,
    val address: String? = null,
    
    // Sync status for offline-first approach
    val isSynced: Boolean = false,
    val syncRetryCount: Int = 0,
    val createdAt: Long = System.currentTimeMillis()
)

/**
 * Location tracking session for duty periods
 */
@Entity(tableName = "location_sessions")
data class LocationSession(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    @SerializedName("duty_id")
    val dutyId: Int,
    val startTime: Long,
    val endTime: Long? = null,
    val totalDistance: Double = 0.0,
    val totalPoints: Int = 0,
    val isActive: Boolean = true,
    val isSynced: Boolean = false
)

/**
 * Location update for API communication
 */
data class LocationUpdateRequest(
    val locations: List<LocationUpdate>
)

data class LocationUpdate(
    val latitude: Double,
    val longitude: Double,
    val accuracy: Float,
    val timestamp: Long,
    @SerializedName("duty_id")
    val dutyId: Int? = null,
    val speed: Float? = null,
    val bearing: Float? = null
)

/**
 * Location sync response from server
 */
data class LocationSyncResponse(
    val success: Boolean,
    val message: String,
    @SerializedName("synced_count")
    val syncedCount: Int? = null,
    val error: String? = null
)

/**
 * Location tracking configuration
 */
data class LocationTrackingConfig(
    val intervalMillis: Long = 30_000L, // 30 seconds default
    val fastestIntervalMillis: Long = 10_000L, // 10 seconds fastest
    val smallestDisplacementMeters: Float = 10f, // 10 meters minimum movement
    val maxWaitTimeMillis: Long = 60_000L, // 1 minute max wait
    val batchSizeLimit: Int = 50, // Max points to sync at once
    val syncIntervalMinutes: Long = 5L // Sync every 5 minutes
)