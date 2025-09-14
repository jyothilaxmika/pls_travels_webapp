package com.plstravels.driver.utils

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat

/**
 * Helper for managing notification permissions, especially for Android 13+
 */
object NotificationPermissionHelper {
    
    const val NOTIFICATION_PERMISSION_REQUEST_CODE = 1003
    
    /**
     * Check if notification permission is required (Android 13+)
     */
    fun isNotificationPermissionRequired(): Boolean {
        return Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
    }
    
    /**
     * Check if notification permission is granted
     */
    fun hasNotificationPermission(context: Context): Boolean {
        return if (isNotificationPermissionRequired()) {
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED
        } else {
            // Permission not required on pre-Android 13
            true
        }
    }
    
    /**
     * Get required notification permissions for Android 13+
     */
    fun getRequiredPermissions(): Array<String> {
        return if (isNotificationPermissionRequired()) {
            arrayOf(Manifest.permission.POST_NOTIFICATIONS)
        } else {
            emptyArray()
        }
    }
    
    /**
     * Check if notification permission should be requested
     * Only needed for Android 13+ and when not already granted
     */
    fun shouldRequestNotificationPermission(context: Context): Boolean {
        return isNotificationPermissionRequired() && !hasNotificationPermission(context)
    }
    
    /**
     * Check if notifications are enabled for the app (overall system setting)
     * This is different from the POST_NOTIFICATIONS permission
     */
    fun areNotificationsEnabled(context: Context): Boolean {
        return androidx.core.app.NotificationManagerCompat.from(context).areNotificationsEnabled()
    }
    
    /**
     * Get missing notification permissions that need to be requested
     */
    fun getMissingNotificationPermissions(context: Context): Array<String> {
        return if (shouldRequestNotificationPermission(context)) {
            getRequiredPermissions()
        } else {
            emptyArray()
        }
    }
    
    /**
     * Check if app has all necessary notification capabilities
     * Includes both permission (Android 13+) and system notification setting
     */
    fun hasFullNotificationAccess(context: Context): Boolean {
        return hasNotificationPermission(context) && areNotificationsEnabled(context)
    }
}