package com.plstravels.driver.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.plstravels.driver.R
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.*
import javax.inject.Inject

/**
 * Background service for handling data synchronization
 * Runs with low priority to minimize battery impact
 */
@AndroidEntryPoint
class SyncService : Service() {
    
    @Inject
    lateinit var syncManager: SyncManager
    
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    
    companion object {
        private const val TAG = "SyncService"
        private const val NOTIFICATION_ID = 1001
        private const val SYNC_CHANNEL_ID = "pls_driver_sync"
        const val ACTION_START_SYNC = "com.plstravels.driver.action.START_SYNC"
        const val ACTION_STOP_SYNC = "com.plstravels.driver.action.STOP_SYNC"
        
        fun startSync(context: Context) {
            val intent = Intent(context, SyncService::class.java).apply {
                action = ACTION_START_SYNC
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }
        
        fun stopSync(context: Context) {
            val intent = Intent(context, SyncService::class.java).apply {
                action = ACTION_STOP_SYNC
            }
            context.startService(intent)
        }
    }
    
    override fun onCreate() {
        super.onCreate()
        createSyncNotificationChannel()
        Log.d(TAG, "SyncService created")
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d(TAG, "SyncService started with action: ${intent?.action}")
        
        when (intent?.action) {
            ACTION_START_SYNC -> {
                startSyncOperation()
                return START_STICKY // Restart if killed
            }
            ACTION_STOP_SYNC -> {
                stopSyncOperation()
                return START_NOT_STICKY
            }
        }
        
        return START_NOT_STICKY
    }
    
    override fun onBind(intent: Intent?): IBinder? = null
    
    override fun onDestroy() {
        super.onDestroy()
        Log.d(TAG, "SyncService destroyed")
        scope.cancel()
        syncManager.shutdown()
    }
    
    private fun startSyncOperation() {
        scope.launch {
            try {
                // Initialize sync manager
                syncManager.initialize()
                
                // Create notification for foreground service
                val notification = NotificationCompat.Builder(this@SyncService, SYNC_CHANNEL_ID)
                    .setContentTitle("Syncing data...")
                    .setContentText("Synchronizing offline data with server")
                    .setSmallIcon(R.drawable.ic_notification)
                    .setPriority(NotificationCompat.PRIORITY_LOW)
                    .setOngoing(true)
                    .build()
                
                // Start foreground service with notification
                startForeground(NOTIFICATION_ID, notification)
                
                // Trigger initial sync
                val syncedCount = syncManager.triggerSync()
                
                if (syncedCount > 0) {
                    updateNotification("Sync completed", "$syncedCount operations synchronized")
                    delay(2000) // Show completion message for 2 seconds
                }
                
                // Update notification to indicate background sync is active
                updateNotification(
                    "Background sync active",
                    "Will sync when data or connectivity changes"
                )
                
            } catch (e: Exception) {
                Log.e(TAG, "Error during sync operation", e)
                updateNotification("Sync error", "Failed to synchronize data")
                delay(3000)
                stopSelf()
            }
        }
    }
    
    private fun stopSyncOperation() {
        Log.d(TAG, "Stopping sync operation")
        syncManager.shutdown()
        stopForeground(true)
        stopSelf()
    }
    
    private fun updateNotification(title: String, content: String) {
        try {
            val notification = NotificationCompat.Builder(this, SYNC_CHANNEL_ID)
                .setContentTitle(title)
                .setContentText(content)
                .setSmallIcon(R.drawable.ic_notification)
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .setOngoing(false)
                .build()
            
            val notificationManager = NotificationManagerCompat.from(this)
            notificationManager.notify(NOTIFICATION_ID, notification)
        } catch (e: Exception) {
            Log.e(TAG, "Error updating notification", e)
        }
    }
    
    /**
     * Create notification channel for sync service
     */
    private fun createSyncNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            
            val syncChannel = NotificationChannel(
                SYNC_CHANNEL_ID,
                "Data Synchronization",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Notifications for background data synchronization"
                enableVibration(false)
                enableLights(false)
                setShowBadge(false)
            }
            
            notificationManager.createNotificationChannel(syncChannel)
        }
    }
}