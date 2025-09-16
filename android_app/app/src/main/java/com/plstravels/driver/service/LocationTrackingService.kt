package com.plstravels.driver.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.plstravels.driver.PLSTravelsApplication
import com.plstravels.driver.R
import com.plstravels.driver.ui.MainActivity
import timber.log.Timber

/**
 * Foreground service for location tracking during duty
 */
class LocationTrackingService : Service() {
    
    override fun onBind(intent: Intent?): IBinder? = null
    
    override fun onCreate() {
        super.onCreate()
        Timber.d("LocationTrackingService created")
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START_TRACKING -> startLocationTracking()
            ACTION_STOP_TRACKING -> stopLocationTracking()
        }
        return START_STICKY
    }
    
    private fun startLocationTracking() {
        Timber.d("Starting location tracking")
        
        val notification = createNotification()
        startForeground(PLSTravelsApplication.LOCATION_SERVICE_NOTIFICATION_ID, notification)
        
        // TODO: Start location updates
        // startLocationUpdates()
    }
    
    private fun stopLocationTracking() {
        Timber.d("Stopping location tracking")
        
        // TODO: Stop location updates
        // stopLocationUpdates()
        
        stopForeground(true)
        stopSelf()
    }
    
    private fun createNotification(): Notification {
        val notificationIntent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this, 0, notificationIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        return NotificationCompat.Builder(this, PLSTravelsApplication.LOCATION_SERVICE_CHANNEL_ID)
            .setContentTitle("PLS Travels - Tracking Location")
            .setContentText("Location tracking is active during duty")
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }
    
    companion object {
        const val ACTION_START_TRACKING = "START_TRACKING"
        const val ACTION_STOP_TRACKING = "STOP_TRACKING"
        
        fun startService(context: Context) {
            val intent = Intent(context, LocationTrackingService::class.java).apply {
                action = ACTION_START_TRACKING
            }
            context.startForegroundService(intent)
        }
        
        fun stopService(context: Context) {
            val intent = Intent(context, LocationTrackingService::class.java).apply {
                action = ACTION_STOP_TRACKING
            }
            context.startService(intent)
        }
    }
}