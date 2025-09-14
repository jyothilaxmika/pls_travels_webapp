package com.plstravels.driver.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.google.gson.Gson
import com.plstravels.driver.MainActivity
import com.plstravels.driver.R
import com.plstravels.driver.data.models.*
import com.plstravels.driver.data.repository.NotificationRepository
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * Firebase Cloud Messaging service for handling push notifications
 */
@AndroidEntryPoint
class FCMService : FirebaseMessagingService() {
    
    @Inject
    lateinit var notificationRepository: NotificationRepository
    
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val gson = Gson()
    
    companion object {
        private const val CHANNEL_ID_DEFAULT = "pls_driver_default"
        private const val CHANNEL_ID_EMERGENCY = "pls_driver_emergency"
        private const val CHANNEL_ID_DUTY = "pls_driver_duty"
        private const val CHANNEL_ID_DISPATCH = "pls_driver_dispatch"
        
        private const val NOTIFICATION_ID_DEFAULT = 1000
        private const val NOTIFICATION_ID_EMERGENCY = 2000
    }
    
    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
    }
    
    override fun onNewToken(token: String) {
        super.onNewToken(token)
        
        // Send new token to server
        serviceScope.launch {
            try {
                notificationRepository.updateFCMToken(token)
            } catch (e: Exception) {
                // Token will be sent on next app start
            }
        }
    }
    
    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        super.onMessageReceived(remoteMessage)
        
        serviceScope.launch {
            try {
                handleIncomingMessage(remoteMessage)
            } catch (e: Exception) {
                // Log error but don't crash the service
            }
        }
    }
    
    private suspend fun handleIncomingMessage(remoteMessage: RemoteMessage) {
        // Parse FCM payload
        val payload = parseFCMPayload(remoteMessage)
        
        // Convert to local notification
        val notification = createNotificationFromPayload(payload)
        
        // Store in local database
        val notificationId = notificationRepository.saveNotification(notification)
        
        // Display notification if app is in background or user preferences allow
        if (shouldDisplayNotification(notification)) {
            displayNotification(notification.copy(id = notificationId))
        }
        
        // Handle special actions
        handleNotificationActions(notification)
    }
    
    private fun parseFCMPayload(remoteMessage: RemoteMessage): FCMNotificationPayload {
        val data = remoteMessage.data
        val notification = remoteMessage.notification
        
        return FCMNotificationPayload(
            title = notification?.title ?: data["title"] ?: "PLS Travels",
            body = notification?.body ?: data["body"] ?: "",
            type = data["type"] ?: "GENERAL",
            notificationId = data["notification_id"] ?: System.currentTimeMillis().toString(),
            senderId = data["sender_id"],
            senderName = data["sender_name"],
            dutyId = data["duty_id"],
            vehicleId = data["vehicle_id"],
            priority = data["priority"],
            expiresAt = data["expires_at"],
            actionType = data["action_type"],
            actionData = data["action_data"],
            data = data.toMap()
        )
    }
    
    private fun createNotificationFromPayload(payload: FCMNotificationPayload): Notification {
        return Notification(
            notificationId = payload.notificationId,
            title = payload.title,
            message = payload.body,
            type = try { NotificationType.valueOf(payload.type) } catch (e: Exception) { NotificationType.GENERAL },
            senderId = payload.senderId?.toIntOrNull(),
            senderName = payload.senderName,
            dutyId = payload.dutyId?.toIntOrNull(),
            vehicleId = payload.vehicleId?.toIntOrNull(),
            data = gson.toJson(payload.data),
            priority = try { 
                NotificationPriority.valueOf(payload.priority ?: "NORMAL") 
            } catch (e: Exception) { 
                NotificationPriority.NORMAL 
            },
            expiresAt = payload.expiresAt?.toLongOrNull(),
            actionType = payload.actionType,
            actionData = payload.actionData
        )
    }
    
    private fun shouldDisplayNotification(notification: Notification): Boolean {
        // Always display high priority notifications
        if (notification.priority.level >= NotificationPriority.HIGH.level) {
            return true
        }
        
        // Check if notification is expired
        if (notification.expiresAt != null && notification.expiresAt < System.currentTimeMillis()) {
            return false
        }
        
        // Default: display notification
        return true
    }
    
    private fun displayNotification(notification: Notification) {
        val channelId = getChannelIdForNotification(notification)
        val notificationId = generateConsistentNotificationId(notification.notificationId)
        
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("notification_id", notification.notificationId)
            putExtra("notification_db_id", notification.id)
            putExtra("notification_type", notification.type.name)
        }
        
        val pendingIntent = PendingIntent.getActivity(
            this,
            notificationId,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        val notificationBuilder = NotificationCompat.Builder(this, channelId)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(notification.title)
            .setContentText(notification.message)
            .setStyle(NotificationCompat.BigTextStyle().bigText(notification.message))
            .setPriority(getAndroidPriority(notification.priority))
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .setWhen(notification.timestamp)
            .setShowWhen(true)
        
        // Add sender info if available
        notification.senderName?.let { sender ->
            notificationBuilder.setSubText("From: $sender")
        }
        
        // Emergency notifications are persistent
        if (notification.priority == NotificationPriority.EMERGENCY) {
            notificationBuilder.setOngoing(true)
            notificationBuilder.setCategory(NotificationCompat.CATEGORY_ALARM)
        }
        
        // Add action buttons for certain notification types
        addNotificationActions(notificationBuilder, notification, notificationId)
        
        try {
            NotificationManagerCompat.from(this).notify(notificationId, notificationBuilder.build())
            
            // Mark as displayed
            serviceScope.launch {
                notificationRepository.markAsDisplayed(notification.id)
            }
        } catch (e: SecurityException) {
            // Notification permission not granted
        }
    }
    
    private fun addNotificationActions(
        builder: NotificationCompat.Builder,
        notification: Notification,
        notificationId: Int
    ) {
        when (notification.type) {
            NotificationType.DUTY_ASSIGNMENT -> {
                val acceptIntent = createActionIntent("ACCEPT_DUTY", notification)
                val acceptPendingIntent = PendingIntent.getBroadcast(
                    this, notificationId + 1, acceptIntent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )
                builder.addAction(R.drawable.ic_check, "Accept", acceptPendingIntent)
            }
            
            NotificationType.DISPATCH_MESSAGE -> {
                val replyIntent = createActionIntent("REPLY_MESSAGE", notification)
                val replyPendingIntent = PendingIntent.getBroadcast(
                    this, notificationId + 2, replyIntent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )
                builder.addAction(R.drawable.ic_reply, "Reply", replyPendingIntent)
            }
            
            else -> {
                // Default: just mark as read
                val readIntent = createActionIntent("MARK_READ", notification)
                val readPendingIntent = PendingIntent.getBroadcast(
                    this, notificationId + 3, readIntent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )
                builder.addAction(R.drawable.ic_check, "Mark Read", readPendingIntent)
            }
        }
    }
    
    private fun createActionIntent(action: String, notification: Notification): Intent {
        return Intent(this, NotificationActionReceiver::class.java).apply {
            putExtra("action", action)
            putExtra("notification_id", notification.notificationId)
            putExtra("notification_db_id", notification.id)
            putExtra("notification_type", notification.type.name)
        }
    }
    
    private suspend fun handleNotificationActions(notification: Notification) {
        when (notification.actionType) {
            "AUTO_ACCEPT_DUTY" -> {
                // Automatically handle duty acceptance
                notificationRepository.handleDutyAssignment(notification)
            }
            "UPDATE_ROUTE" -> {
                // Handle route updates
                notificationRepository.handleRouteUpdate(notification)
            }
            // Add more action types as needed
        }
    }
    
    private fun getChannelIdForNotification(notification: Notification): String {
        return when (notification.type) {
            NotificationType.EMERGENCY_ALERT -> CHANNEL_ID_EMERGENCY
            NotificationType.DUTY_ASSIGNMENT, NotificationType.ROUTE_UPDATE -> CHANNEL_ID_DUTY
            NotificationType.DISPATCH_MESSAGE -> CHANNEL_ID_DISPATCH
            else -> CHANNEL_ID_DEFAULT
        }
    }
    
    private fun generateConsistentNotificationId(externalId: String): Int {
        // Generate consistent notification ID from external notification ID
        return externalId.hashCode().let { hash ->
            // Ensure positive value and avoid collision with reserved ranges
            Math.abs(hash) % 100000 + 10000
        }
    }
    
    private fun getAndroidPriority(priority: NotificationPriority): Int {
        return when (priority) {
            NotificationPriority.LOW -> NotificationCompat.PRIORITY_LOW
            NotificationPriority.NORMAL -> NotificationCompat.PRIORITY_DEFAULT
            NotificationPriority.HIGH -> NotificationCompat.PRIORITY_HIGH
            NotificationPriority.URGENT, NotificationPriority.EMERGENCY -> NotificationCompat.PRIORITY_MAX
        }
    }
    
    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            
            // Default channel
            val defaultChannel = NotificationChannel(
                CHANNEL_ID_DEFAULT,
                "General Notifications",
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = "General PLS Travels notifications"
                enableVibration(true)
                enableLights(true)
            }
            
            // Emergency channel
            val emergencyChannel = NotificationChannel(
                CHANNEL_ID_EMERGENCY,
                "Emergency Alerts",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Critical emergency alerts"
                enableVibration(true)
                enableLights(true)
                // Use default sound for emergency alerts - don't set to null
            }
            
            // Duty channel
            val dutyChannel = NotificationChannel(
                CHANNEL_ID_DUTY,
                "Duty Updates",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Duty assignments and route updates"
                enableVibration(true)
                enableLights(true)
            }
            
            // Dispatch channel
            val dispatchChannel = NotificationChannel(
                CHANNEL_ID_DISPATCH,
                "Dispatch Messages",
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = "Messages from dispatch and management"
                enableVibration(true)
                enableLights(true)
            }
            
            notificationManager.createNotificationChannels(listOf(
                defaultChannel, emergencyChannel, dutyChannel, dispatchChannel
            ))
        }
    }
}