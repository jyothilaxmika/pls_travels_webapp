package com.plstravels.driver

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import androidx.work.WorkManager
import dagger.hilt.android.HiltAndroidApp
import timber.log.Timber
import javax.inject.Inject

/**
 * PLS Travels Driver Application
 * Entry point for the Android application with Hilt dependency injection
 */
@HiltAndroidApp
class PLSTravelsApplication : Application(), Configuration.Provider {

    @Inject
    lateinit var workerFactory: HiltWorkerFactory

    override fun onCreate() {
        super.onCreate()
        
        // Initialize logging
        initializeLogging()
        
        // Create notification channels
        createNotificationChannels()
        
        // Initialize Work Manager with Hilt
        initializeWorkManager()
        
        Timber.i("PLS Travels Driver Application started successfully")
    }

    override fun getWorkManagerConfiguration(): Configuration {
        return Configuration.Builder()
            .setWorkerFactory(workerFactory)
            .setMinimumLoggingLevel(if (BuildConfig.DEBUG) android.util.Log.DEBUG else android.util.Log.ERROR)
            .build()
    }

    private fun initializeLogging() {
        if (BuildConfig.DEBUG) {
            Timber.plant(Timber.DebugTree())
        } else {
            // Production logging (Firebase Crashlytics integration)
            Timber.plant(ProductionTree())
        }
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            
            // Duty notifications channel
            val dutyChannel = NotificationChannel(
                DUTY_NOTIFICATION_CHANNEL_ID,
                "Duty Notifications",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Notifications for duty assignments and updates"
                enableVibration(true)
                enableLights(true)
            }
            
            // Location tracking channel
            val locationChannel = NotificationChannel(
                LOCATION_SERVICE_CHANNEL_ID,
                "Location Tracking",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Background location tracking service"
                enableVibration(false)
                enableLights(false)
            }
            
            // Emergency notifications channel
            val emergencyChannel = NotificationChannel(
                EMERGENCY_NOTIFICATION_CHANNEL_ID,
                "Emergency Alerts",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Critical emergency notifications"
                enableVibration(true)
                enableLights(true)
                setBypassDnd(true)
            }
            
            // Admin messages channel
            val adminChannel = NotificationChannel(
                ADMIN_NOTIFICATION_CHANNEL_ID,
                "Admin Messages",
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = "Messages from admin and management"
                enableVibration(true)
            }
            
            notificationManager.createNotificationChannels(
                listOf(dutyChannel, locationChannel, emergencyChannel, adminChannel)
            )
        }
    }

    private fun initializeWorkManager() {
        try {
            WorkManager.initialize(this, workManagerConfiguration)
        } catch (e: IllegalStateException) {
            // WorkManager already initialized
            Timber.w("WorkManager already initialized: ${e.message}")
        }
    }

    companion object {
        // Notification Channel IDs
        const val DUTY_NOTIFICATION_CHANNEL_ID = "duty_notifications"
        const val LOCATION_SERVICE_CHANNEL_ID = "location_service"
        const val EMERGENCY_NOTIFICATION_CHANNEL_ID = "emergency_notifications"
        const val ADMIN_NOTIFICATION_CHANNEL_ID = "admin_notifications"
        
        // Notification IDs
        const val DUTY_NOTIFICATION_ID = 1001
        const val LOCATION_SERVICE_NOTIFICATION_ID = 1002
        const val EMERGENCY_NOTIFICATION_ID = 1003
        const val ADMIN_NOTIFICATION_ID = 1004
    }
}

/**
 * Production logging tree for release builds
 * Integrates with Firebase Crashlytics for error reporting
 */
class ProductionTree : Timber.Tree() {
    override fun log(priority: Int, tag: String?, message: String, t: Throwable?) {
        // Only log warnings and errors in production
        if (priority >= android.util.Log.WARN) {
            // Send to Firebase Crashlytics
            if (t != null) {
                // Log exception to Crashlytics
                com.google.firebase.crashlytics.FirebaseCrashlytics.getInstance().recordException(t)
            } else {
                // Log message to Crashlytics
                com.google.firebase.crashlytics.FirebaseCrashlytics.getInstance().log(message)
            }
        }
    }
}