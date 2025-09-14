package com.plstravels.driver.data.repository

import android.content.Context
import android.content.SharedPreferences
import com.google.firebase.messaging.FirebaseMessaging
import com.plstravels.driver.data.local.NotificationDao
import com.plstravels.driver.data.models.*
import com.plstravels.driver.data.network.ApiService
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.tasks.await
import javax.inject.Inject
import javax.inject.Singleton
import dagger.hilt.android.qualifiers.ApplicationContext

/**
 * Repository for notification management and FCM operations
 */
@Singleton
class NotificationRepository @Inject constructor(
    private val apiService: ApiService,
    private val notificationDao: NotificationDao,
    @ApplicationContext private val context: Context
) {
    
    private val prefs: SharedPreferences = context.getSharedPreferences("fcm_prefs", Context.MODE_PRIVATE)
    
    companion object {
        private const val PREF_FCM_TOKEN = "fcm_token"
        private const val PREF_TOKEN_SENT = "token_sent"
        private const val PREF_DEVICE_ID = "device_id"
    }
    
    fun getAllNotifications(): Flow<List<Notification>> = notificationDao.getAllNotifications()
    
    fun getUnreadNotifications(): Flow<List<Notification>> = notificationDao.getUnreadNotifications()
    
    fun getNotificationsByType(type: NotificationType): Flow<List<Notification>> = 
        notificationDao.getNotificationsByType(type)
    
    fun getNotificationsForDuty(dutyId: Int): Flow<List<Notification>> = 
        notificationDao.getNotificationsForDuty(dutyId)
    
    suspend fun getUnreadCount(): Int = notificationDao.getUnreadCount()
    
    suspend fun getUnreadHighPriorityCount(): Int = 
        notificationDao.getUnreadCountByPriority(
            listOf(NotificationPriority.HIGH, NotificationPriority.URGENT, NotificationPriority.EMERGENCY)
        )
    
    suspend fun saveNotification(notification: Notification): Long {
        return notificationDao.insertNotification(notification)
    }
    
    suspend fun markAsRead(notificationId: Long) {
        notificationDao.markAsRead(notificationId)
    }
    
    suspend fun markAsDisplayed(notificationId: Long) {
        notificationDao.markAsDisplayed(notificationId)
    }
    
    suspend fun markAllAsRead() {
        notificationDao.markAllAsRead()
    }
    
    suspend fun deleteNotification(notificationId: Long) {
        notificationDao.deleteNotificationById(notificationId)
    }
    
    suspend fun deleteExpiredNotifications() {
        notificationDao.deleteExpiredNotifications()
    }
    
    suspend fun cleanupOldNotifications() {
        // Delete read notifications older than 30 days
        val cutoffTime = System.currentTimeMillis() - (30 * 24 * 60 * 60 * 1000L)
        notificationDao.deleteOldReadNotifications(cutoffTime)
        
        // Delete expired notifications
        deleteExpiredNotifications()
    }
    
    /**
     * Get or generate FCM token and register with server
     */
    suspend fun initializeFCM(): Result<String> {
        return try {
            val token = FirebaseMessaging.getInstance().token.await()
            
            // Store token locally
            prefs.edit().putString(PREF_FCM_TOKEN, token).apply()
            
            // Send to server if not already sent
            if (!prefs.getBoolean(PREF_TOKEN_SENT, false)) {
                updateFCMToken(token)
            }
            
            Result.success(token)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Update FCM token on server
     */
    suspend fun updateFCMToken(token: String): Result<FCMTokenResponse> {
        return try {
            val deviceId = getDeviceId()
            val appVersion = getAppVersion()
            
            val request = FCMTokenRequest(
                fcmToken = token,
                deviceId = deviceId,
                appVersion = appVersion
            )
            
            val response = apiService.updateFCMToken(request)
            
            if (response.isSuccessful && response.body()?.success == true) {
                // Mark token as sent
                prefs.edit()
                    .putString(PREF_FCM_TOKEN, token)
                    .putBoolean(PREF_TOKEN_SENT, true)
                    .apply()
                
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Failed to update FCM token: ${response.body()?.message}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Subscribe to notification topics
     */
    suspend fun subscribeToTopics(topics: List<String>): Result<Unit> {
        return try {
            topics.forEach { topic ->
                FirebaseMessaging.getInstance().subscribeToTopic(topic).await()
            }
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Unsubscribe from notification topics
     */
    suspend fun unsubscribeFromTopics(topics: List<String>): Result<Unit> {
        return try {
            topics.forEach { topic ->
                FirebaseMessaging.getInstance().unsubscribeFromTopic(topic).await()
            }
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Handle duty assignment from notification
     */
    suspend fun handleDutyAssignment(notification: Notification) {
        // Parse duty data from notification
        val dutyId = notification.dutyId
        if (dutyId != null) {
            // Mark notification as read
            markAsRead(notification.id)
            
            // Could trigger duty repository to fetch updated duty data
            // dutyRepository.refreshDuty(dutyId)
        }
    }
    
    /**
     * Handle duty acceptance from notification action
     */
    suspend fun handleDutyAcceptance(notificationId: Long) {
        val notification = notificationDao.getNotificationById(notificationId)
        if (notification != null && notification.dutyId != null) {
            try {
                // Call API to accept duty
                val response = apiService.acceptDutyAssignment(notification.dutyId)
                
                if (response.isSuccessful) {
                    // Create success notification
                    val successNotification = Notification(
                        notificationId = "duty_accepted_${notification.dutyId}",
                        title = "Duty Accepted",
                        message = "You have successfully accepted the duty assignment.",
                        type = NotificationType.SYSTEM_UPDATE,
                        priority = NotificationPriority.NORMAL
                    )
                    saveNotification(successNotification)
                }
            } catch (e: Exception) {
                // Create error notification
                val errorNotification = Notification(
                    notificationId = "duty_accept_error_${notification.dutyId}",
                    title = "Duty Acceptance Failed",
                    message = "Failed to accept duty assignment. Please try again.",
                    type = NotificationType.SYSTEM_UPDATE,
                    priority = NotificationPriority.HIGH
                )
                saveNotification(errorNotification)
            }
        }
    }
    
    /**
     * Handle route update from notification
     */
    suspend fun handleRouteUpdate(notification: Notification) {
        // Parse route data and update local storage
        notification.dutyId?.let { dutyId ->
            markAsRead(notification.id)
            // Could trigger location repository to update route
        }
    }
    
    /**
     * Create and send local notification for testing
     */
    suspend fun createTestNotification(type: NotificationType = NotificationType.GENERAL) {
        val testNotification = Notification(
            notificationId = "test_${System.currentTimeMillis()}",
            title = "Test Notification",
            message = "This is a test notification to verify the system is working correctly.",
            type = type,
            senderName = "System",
            priority = NotificationPriority.NORMAL
        )
        
        saveNotification(testNotification)
    }
    
    private fun getDeviceId(): String {
        val existing = prefs.getString(PREF_DEVICE_ID, null)
        if (existing != null) return existing
        
        val newId = java.util.UUID.randomUUID().toString()
        prefs.edit().putString(PREF_DEVICE_ID, newId).apply()
        return newId
    }
    
    private fun getAppVersion(): String {
        return try {
            val packageInfo = context.packageManager.getPackageInfo(context.packageName, 0)
            packageInfo.versionName ?: "1.0"
        } catch (e: Exception) {
            "1.0"
        }
    }
}