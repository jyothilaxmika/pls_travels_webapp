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
        val notificationId = intent.getLongExtra("notification_id", -1)
        
        if (notificationId == -1L) return
        
        scope.launch {
            handleAction(action, notificationId, context)
        }
    }
    
    private suspend fun handleAction(action: String, notificationId: Long, context: Context) {
        when (action) {
            "MARK_READ" -> {
                notificationRepository.markAsRead(notificationId)
                // Cancel the notification
                androidx.core.app.NotificationManagerCompat.from(context).cancel(notificationId.toInt())
            }
            
            "ACCEPT_DUTY" -> {
                notificationRepository.markAsRead(notificationId)
                notificationRepository.handleDutyAcceptance(notificationId)
                androidx.core.app.NotificationManagerCompat.from(context).cancel(notificationId.toInt())
            }
            
            "REPLY_MESSAGE" -> {
                // Open app to reply screen
                val mainIntent = Intent(context, com.plstravels.driver.MainActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                    putExtra("action", "REPLY_MESSAGE")
                    putExtra("notification_id", notificationId)
                }
                context.startActivity(mainIntent)
            }
        }
    }
}