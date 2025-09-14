package com.plstravels.driver.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.plstravels.driver.data.repository.NotificationRepository
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * Handles notification action button clicks
 */
@AndroidEntryPoint
class NotificationActionReceiver : BroadcastReceiver() {
    
    @Inject
    lateinit var notificationRepository: NotificationRepository
    
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    
    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.getStringExtra("action") ?: return
        val notificationId = intent.getStringExtra("notification_id") ?: return
        val notificationDbId = intent.getLongExtra("notification_db_id", -1)
        
        if (notificationDbId == -1L) return
        
        scope.launch {
            handleAction(action, notificationId, notificationDbId, context)
        }
    }
    
    private suspend fun handleAction(action: String, notificationId: String, notificationDbId: Long, context: Context) {
        // Generate consistent display notification ID for cancellation
        val displayNotificationId = generateConsistentNotificationId(notificationId)
        
        when (action) {
            "MARK_READ" -> {
                notificationRepository.markAsRead(notificationDbId)
                // Cancel the notification using the display ID
                androidx.core.app.NotificationManagerCompat.from(context).cancel(displayNotificationId)
            }
            
            "ACCEPT_DUTY" -> {
                notificationRepository.markAsRead(notificationDbId)
                notificationRepository.handleDutyAcceptance(notificationDbId)
                androidx.core.app.NotificationManagerCompat.from(context).cancel(displayNotificationId)
            }
            
            "REPLY_MESSAGE" -> {
                // Open app to reply screen
                val mainIntent = Intent(context, com.plstravels.driver.MainActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                    putExtra("action", "REPLY_MESSAGE")
                    putExtra("notification_id", notificationId)
                    putExtra("notification_db_id", notificationDbId)
                }
                context.startActivity(mainIntent)
            }
        }
    }
    
    private fun generateConsistentNotificationId(externalId: String): Int {
        // Must match the same logic in FCMService
        return externalId.hashCode().let { hash ->
            Math.abs(hash) % 100000 + 10000
        }
    }
}