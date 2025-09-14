package com.plstravels.driver.utils

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import androidx.core.content.ContextCompat

/**
 * Helper for camera permission management
 */
object CameraPermissionHelper {
    
    const val CAMERA_PERMISSION = Manifest.permission.CAMERA
    
    /**
     * Check if camera permission is granted
     */
    fun isCameraPermissionGranted(context: Context): Boolean {
        return ContextCompat.checkSelfPermission(
            context,
            CAMERA_PERMISSION
        ) == PackageManager.PERMISSION_GRANTED
    }
    
    /**
     * Get required camera permissions
     */
    fun getRequiredPermissions(): Array<String> {
        return arrayOf(CAMERA_PERMISSION)
    }
}