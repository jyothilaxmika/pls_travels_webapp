package com.plstravels.driver.utils

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat

/**
 * Helper class for managing location permissions
 */
object LocationPermissionHelper {
    
    const val LOCATION_PERMISSION_REQUEST_CODE = 1001
    const val BACKGROUND_LOCATION_PERMISSION_REQUEST_CODE = 1002
    
    /**
     * Required permissions for location tracking
     */
    val LOCATION_PERMISSIONS = arrayOf(
        Manifest.permission.ACCESS_FINE_LOCATION,
        Manifest.permission.ACCESS_COARSE_LOCATION
    )
    
    val BACKGROUND_LOCATION_PERMISSIONS = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
        arrayOf(Manifest.permission.ACCESS_BACKGROUND_LOCATION)
    } else {
        emptyArray()
    }
    
    /**
     * Check if basic location permissions are granted
     */
    fun hasLocationPermissions(context: Context): Boolean {
        return LOCATION_PERMISSIONS.all { permission ->
            ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED
        }
    }
    
    /**
     * Check if background location permission is granted (Android 10+)
     */
    fun hasBackgroundLocationPermission(context: Context): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.ACCESS_BACKGROUND_LOCATION
            ) == PackageManager.PERMISSION_GRANTED
        } else {
            // Background location is included in foreground permission for Android 9 and below
            hasLocationPermissions(context)
        }
    }
    
    /**
     * Check if all required permissions for duty tracking are granted
     */
    fun hasAllRequiredPermissions(context: Context): Boolean {
        return hasLocationPermissions(context) && hasBackgroundLocationPermission(context)
    }
    
    /**
     * Get permissions that need to be requested
     */
    fun getMissingPermissions(context: Context): Array<String> {
        val missingPermissions = mutableListOf<String>()
        
        // Check basic location permissions
        LOCATION_PERMISSIONS.forEach { permission ->
            if (ContextCompat.checkSelfPermission(context, permission) != PackageManager.PERMISSION_GRANTED) {
                missingPermissions.add(permission)
            }
        }
        
        return missingPermissions.toTypedArray()
    }
    
    /**
     * Get background location permissions that need to be requested
     * Should be called only after basic location permissions are granted
     */
    fun getMissingBackgroundPermissions(context: Context): Array<String> {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            if (!hasBackgroundLocationPermission(context)) {
                BACKGROUND_LOCATION_PERMISSIONS
            } else {
                emptyArray()
            }
        } else {
            emptyArray()
        }
    }
}