package com.plstravels.driver.utils

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.activity.result.ActivityResultLauncher
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import timber.log.Timber

/**
 * Helper class for managing location permissions
 */
class LocationPermissionHelper(private val context: Context) {

    companion object {
        private val REQUIRED_LOCATION_PERMISSIONS = arrayOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION
        )
        
        private val BACKGROUND_LOCATION_PERMISSION = 
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                arrayOf(Manifest.permission.ACCESS_BACKGROUND_LOCATION)
            } else {
                emptyArray()
            }
    }

    /**
     * Check if all required location permissions are granted
     */
    fun hasLocationPermissions(): Boolean {
        return REQUIRED_LOCATION_PERMISSIONS.all { permission ->
            ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED
        }
    }

    /**
     * Check if background location permission is granted
     */
    fun hasBackgroundLocationPermission(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ContextCompat.checkSelfPermission(
                context, 
                Manifest.permission.ACCESS_BACKGROUND_LOCATION
            ) == PackageManager.PERMISSION_GRANTED
        } else {
            true // Not required for older versions
        }
    }

    /**
     * Check if we should show rationale for location permissions
     * Note: This method only works when called from an Activity context
     */
    fun shouldShowLocationPermissionRationale(): Boolean {
        return if (context is androidx.activity.ComponentActivity) {
            REQUIRED_LOCATION_PERMISSIONS.any { permission ->
                ActivityCompat.shouldShowRequestPermissionRationale(
                    context as androidx.activity.ComponentActivity, 
                    permission
                )
            }
        } else {
            // Return false when called from Service context
            false
        }
    }

    /**
     * Check if we should show rationale for background location permission
     * Note: This method only works when called from an Activity context
     */
    fun shouldShowBackgroundLocationPermissionRationale(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q && context is androidx.activity.ComponentActivity) {
            ActivityCompat.shouldShowRequestPermissionRationale(
                context as androidx.activity.ComponentActivity,
                Manifest.permission.ACCESS_BACKGROUND_LOCATION
            )
        } else {
            false
        }
    }

    /**
     * Get required location permissions to request
     */
    fun getRequiredLocationPermissions(): Array<String> {
        return REQUIRED_LOCATION_PERMISSIONS
    }

    /**
     * Get background location permission to request
     */
    fun getBackgroundLocationPermission(): Array<String> {
        return BACKGROUND_LOCATION_PERMISSION
    }

    /**
     * Check location permission status and return appropriate state
     */
    fun getLocationPermissionState(): LocationPermissionState {
        return when {
            !hasLocationPermissions() -> LocationPermissionState.DENIED
            hasLocationPermissions() && !hasBackgroundLocationPermission() -> LocationPermissionState.GRANTED_FOREGROUND_ONLY
            hasLocationPermissions() && hasBackgroundLocationPermission() -> LocationPermissionState.GRANTED_ALL
            else -> LocationPermissionState.DENIED
        }
    }

    /**
     * Open app settings to allow user to manually grant permissions
     */
    fun openAppSettings() {
        try {
            val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                data = Uri.fromParts("package", context.packageName, null)
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            }
            context.startActivity(intent)
        } catch (e: Exception) {
            Timber.e(e, "Failed to open app settings")
            // Fallback to general settings
            try {
                val intent = Intent(Settings.ACTION_SETTINGS).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK
                }
                context.startActivity(intent)
            } catch (ex: Exception) {
                Timber.e(ex, "Failed to open settings")
            }
        }
    }

    /**
     * Create permission explanation message
     */
    fun getLocationPermissionExplanation(): String {
        return when (getLocationPermissionState()) {
            LocationPermissionState.DENIED -> {
                "PLS Travels needs location access to track your route during duties. " +
                "This helps ensure accurate duty logging and enables fleet management features."
            }
            LocationPermissionState.GRANTED_FOREGROUND_ONLY -> {
                "For accurate duty tracking, PLS Travels needs background location access. " +
                "This allows the app to track your route even when minimized, ensuring complete duty logs."
            }
            LocationPermissionState.GRANTED_ALL -> {
                "All location permissions granted. You're ready to start duty tracking!"
            }
        }
    }

    /**
     * Get user-friendly permission status
     */
    fun getPermissionStatusMessage(): String {
        return when (getLocationPermissionState()) {
            LocationPermissionState.DENIED -> "Location access required"
            LocationPermissionState.GRANTED_FOREGROUND_ONLY -> "Background location recommended"
            LocationPermissionState.GRANTED_ALL -> "All permissions granted ✓"
        }
    }

    /**
     * Check if precise location is available (Android 12+)
     */
    fun hasPreciseLocationPermission(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            ContextCompat.checkSelfPermission(
                context, 
                Manifest.permission.ACCESS_FINE_LOCATION
            ) == PackageManager.PERMISSION_GRANTED
        } else {
            hasLocationPermissions()
        }
    }
}

/**
 * Location permission states
 */
enum class LocationPermissionState {
    DENIED,
    GRANTED_FOREGROUND_ONLY,
    GRANTED_ALL
}

/**
 * Permission request results
 */
sealed class LocationPermissionResult {
    object Granted : LocationPermissionResult()
    object PartiallyGranted : LocationPermissionResult()
    object Denied : LocationPermissionResult()
    object PermanentlyDenied : LocationPermissionResult()
}