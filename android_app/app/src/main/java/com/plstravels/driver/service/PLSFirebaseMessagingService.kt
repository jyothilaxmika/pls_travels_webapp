package com.plstravels.driver.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.plstravels.driver.R
import com.plstravels.driver.data.repository.AuthRepository
import com.plstravels.driver.ui.MainActivity
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import timber.log.Timber
import javax.inject.Inject

/**
 * Firebase Cloud Messaging service for push notifications
 */
@AndroidEntryPoint
class PLSFirebaseMessagingService : FirebaseMessagingService() {
    
    @Inject
    lateinit var authRepository: AuthRepository
    
    private val serviceScope = CoroutineScope(Dispatchers.IO)
    
    companion object {
        const val NOTIFICATION_CHANNEL_ID = "pls_notifications"
        const val NOTIFICATION_CHANNEL_NAME = "PLS Notifications"
        private const val NOTIFICATION_ID_BASE = 1000
    }
    
    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Timber.d("New FCM token received")
        
        // Send token to server
        sendTokenToServer(token)
    }
    
    /**
     * Send FCM token to server for push notification targeting
     */
    private fun sendTokenToServer(token: String) {
        serviceScope.launch {
            try {
                val result = authRepository.updateFcmToken(token)
                result.fold(
                    onSuccess = {
                        Timber.d("FCM token successfully sent to server")
                    },
                    onFailure = { exception ->
                        Timber.e(exception, "Failed to send FCM token to server")
                    }
                )
            } catch (e: Exception) {
                Timber.e(e, "Error sending FCM token to server")
            }
        }
    }
    
    /**
     * Sync current FCM token with server
     * This method should be called on app start and after login
     */
    fun syncCurrentTokenWithServer() {
        Timber.d("Syncing current FCM token with server")
        com.google.firebase.messaging.FirebaseMessaging.getInstance().token
            .addOnCompleteListener { task ->
                if (!task.isSuccessful) {
                    Timber.w(task.exception, "Fetching FCM registration token failed")
                    return@addOnCompleteListener
                }

                // Get new FCM registration token
                val token = task.result
                Timber.d("Current FCM token retrieved for sync: ${token.take(20)}...")
                
                // Send token to server
                sendTokenToServer(token)
            }
    }
    
    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        super.onMessageReceived(remoteMessage)
        
        Timber.d("FCM message received from: ${remoteMessage.from}")
        
        // Handle notification payload
        remoteMessage.notification?.let { notification ->
            Timber.d("Notification received: ${notification.title}")
            showNotification(
                title = notification.title ?: "PLS Travels",
                body = notification.body ?: "New notification",
                data = remoteMessage.data
            )
        }
        
        // Handle data-only messages
        if (remoteMessage.data.isNotEmpty()) {
            Timber.d("FCM data payload: ${remoteMessage.data}")
            handleDataMessage(remoteMessage.data)
        }
    }
    
    /**
     * Show notification to user
     */
    private fun showNotification(
        title: String,
        body: String,
        data: Map<String, String> = emptyMap()
    ) {
        createNotificationChannel()
        
        // Create intent to open app when notification is tapped
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            // Add extra data from FCM payload
            data.forEach { (key, value) ->
                putExtra(key, value)
            }
        }
        
        val pendingIntent = PendingIntent.getActivity(
            this,
            NOTIFICATION_ID_BASE,
            intent,
            PendingIntent.FLAG_ONE_SHOT or PendingIntent.FLAG_IMMUTABLE
        )
        
        // Determine notification priority based on message type
        val priority = when (data["priority"]) {
            "high" -> NotificationCompat.PRIORITY_HIGH
            "low" -> NotificationCompat.PRIORITY_LOW
            else -> NotificationCompat.PRIORITY_DEFAULT
        }
        
        val notificationBuilder = NotificationCompat.Builder(this, NOTIFICATION_CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_location_24) // Use existing icon
            .setContentTitle(title)
            .setContentText(body)
            .setAutoCancel(true)
            .setPriority(priority)
            .setContentIntent(pendingIntent)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
        
        // Add action buttons based on message type
        addNotificationActions(notificationBuilder, data)
        
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val notificationId = generateNotificationId(data)
        
        try {
            notificationManager.notify(notificationId, notificationBuilder.build())
            Timber.d("Notification displayed: $title")
        } catch (e: Exception) {
            Timber.e(e, "Failed to display notification")
        }
    }
    
    /**
     * Handle data-only messages for background processing
     */
    private fun handleDataMessage(data: Map<String, String>) {
        val messageType = data["type"]
        
        when (messageType) {
            "duty_assignment" -> {
                // Handle duty assignment notifications
                val dutyId = data["duty_id"]
                Timber.d("Received duty assignment: $dutyId")
                showNotification(
                    title = "New Duty Assignment",
                    body = data["message"] ?: "You have been assigned a new duty",
                    data = data
                )
            }
            
            "duty_update" -> {
                // Handle duty status updates
                val status = data["status"]
                Timber.d("Received duty update: $status")
                showNotification(
                    title = "Duty Update",
                    body = data["message"] ?: "Your duty status has been updated",
                    data = data
                )
            }
            
            "emergency_alert" -> {
                // Handle emergency alerts with high priority
                Timber.d("Received emergency alert")
                showNotification(
                    title = "🚨 Emergency Alert",
                    body = data["message"] ?: "Emergency notification",
                    data = data + ("priority" to "high")
                )
            }
            
            "system_message" -> {
                // Handle system messages
                Timber.d("Received system message")
                showNotification(
                    title = data["title"] ?: "System Message",
                    body = data["message"] ?: "System notification",
                    data = data
                )
            }
            
            "silent_sync" -> {
                // Handle silent background sync requests
                Timber.d("Received silent sync request")
                triggerBackgroundSync()
            }
            
            else -> {
                // Handle unknown message types
                Timber.w("Unknown FCM message type: $messageType")
                if (data["message"] != null) {
                    showNotification(
                        title = "PLS Travels",
                        body = data["message"]!!,
                        data = data
                    )
                }
            }
        }
    }
    
    /**
     * Add action buttons to notifications based on message type
     */
    private fun addNotificationActions(
        builder: NotificationCompat.Builder,
        data: Map<String, String>
    ) {
        when (data["type"]) {
            "duty_assignment" -> {
                // Add "View Duty" action
                val viewIntent = Intent(this, MainActivity::class.java).apply {
                    putExtra("action", "view_duty")
                    putExtra("duty_id", data["duty_id"])
                }
                val viewPendingIntent = PendingIntent.getActivity(
                    this,
                    NOTIFICATION_ID_BASE + 1,
                    viewIntent,
                    PendingIntent.FLAG_IMMUTABLE
                )
                builder.addAction(
                    R.drawable.ic_location_24,
                    "View Duty",
                    viewPendingIntent
                )
            }
            
            "emergency_alert" -> {
                // Add "Acknowledge" action for emergency alerts
                val ackIntent = Intent(this, MainActivity::class.java).apply {
                    putExtra("action", "acknowledge_emergency")
                    putExtra("alert_id", data["alert_id"])
                }
                val ackPendingIntent = PendingIntent.getActivity(
                    this,
                    NOTIFICATION_ID_BASE + 2,
                    ackIntent,
                    PendingIntent.FLAG_IMMUTABLE
                )
                builder.addAction(
                    R.drawable.ic_location_24,
                    "Acknowledge",
                    ackPendingIntent
                )
            }
        }
    }
    
    /**
     * Generate unique notification ID based on message content
     */
    private fun generateNotificationId(data: Map<String, String>): Int {
        return data["notification_id"]?.toIntOrNull()
            ?: data["duty_id"]?.hashCode()
            ?: data["alert_id"]?.hashCode()
            ?: NOTIFICATION_ID_BASE + System.currentTimeMillis().toInt()
    }
    
    /**
     * Create notification channel for Android O+
     */
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                NOTIFICATION_CHANNEL_ID,
                NOTIFICATION_CHANNEL_NAME,
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Notifications for PLS Travels app"
                enableLights(true)
                enableVibration(true)
            }
            
            val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }
    
    /**
     * Trigger background sync for silent notifications
     */
    private fun triggerBackgroundSync() {
        try {
            // Trigger background sync service
            val syncIntent = Intent(this, BackgroundSyncService::class.java)
            startService(syncIntent)
            Timber.d("Background sync triggered by FCM")
        } catch (e: Exception) {
            Timber.e(e, "Failed to trigger background sync")
        }
    }
}