package com.plstravels.driver.data.models

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.google.gson.annotations.SerializedName

/**
 * Data models for push notifications and messaging
 */
@Entity(tableName = "notifications")
data class Notification(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    @SerializedName("notification_id")
    val notificationId: String,
    val title: String,
    val message: String,
    val type: NotificationType,
    @SerializedName("sender_id")
    val senderId: Int? = null,
    @SerializedName("sender_name")
    val senderName: String? = null,
    @SerializedName("duty_id")
    val dutyId: Int? = null,
    @SerializedName("vehicle_id")
    val vehicleId: Int? = null,
    val data: String? = null, // JSON string for additional data
    val timestamp: Long = System.currentTimeMillis(),
    
    // Status tracking
    val isRead: Boolean = false,
    val isDisplayed: Boolean = false,
    val readAt: Long? = null,
    
    // Priority and expiry
    val priority: NotificationPriority = NotificationPriority.NORMAL,
    val expiresAt: Long? = null,
    
    // Action data
    val actionType: String? = null,
    val actionData: String? = null
)

/**
 * Types of notifications drivers can receive
 */
enum class NotificationType(val displayName: String, val iconRes: String) {
    DUTY_ASSIGNMENT("Duty Assignment", "assignment"),
    ROUTE_UPDATE("Route Update", "directions"),
    VEHICLE_ALERT("Vehicle Alert", "warning"),
    DISPATCH_MESSAGE("Dispatch Message", "message"),
    EMERGENCY_ALERT("Emergency Alert", "emergency"),
    SYSTEM_UPDATE("System Update", "info"),
    EARNINGS_UPDATE("Earnings Update", "payment"),
    GENERAL("General Message", "notifications")
}

/**
 * Notification priority levels
 */
enum class NotificationPriority(val level: Int) {
    LOW(1),
    NORMAL(2),
    HIGH(3),
    URGENT(4),
    EMERGENCY(5)
}

/**
 * FCM token data for server registration
 */
data class FCMTokenRequest(
    @SerializedName("fcm_token")
    val fcmToken: String,
    @SerializedName("device_id")
    val deviceId: String,
    @SerializedName("platform")
    val platform: String = "android",
    @SerializedName("app_version")
    val appVersion: String
)

/**
 * FCM token response from server
 */
data class FCMTokenResponse(
    val success: Boolean,
    val message: String,
    @SerializedName("token_id")
    val tokenId: String? = null
)

/**
 * Push notification payload from FCM
 */
data class FCMNotificationPayload(
    val title: String,
    val body: String,
    val type: String,
    @SerializedName("notification_id")
    val notificationId: String,
    @SerializedName("sender_id")
    val senderId: String? = null,
    @SerializedName("sender_name")
    val senderName: String? = null,
    @SerializedName("duty_id")
    val dutyId: String? = null,
    @SerializedName("vehicle_id")
    val vehicleId: String? = null,
    val priority: String? = null,
    @SerializedName("expires_at")
    val expiresAt: String? = null,
    @SerializedName("action_type")
    val actionType: String? = null,
    @SerializedName("action_data")
    val actionData: String? = null,
    val data: Map<String, String>? = null
)

/**
 * Notification display configuration
 */
data class NotificationDisplayConfig(
    val showBadge: Boolean = true,
    val playSound: Boolean = true,
    val vibrate: Boolean = true,
    val showInForeground: Boolean = true,
    val autoCancel: Boolean = true,
    val persistentForEmergency: Boolean = true
)