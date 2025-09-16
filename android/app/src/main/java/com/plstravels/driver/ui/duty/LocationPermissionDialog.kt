package com.plstravels.driver.ui.duty

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.plstravels.driver.utils.LocationPermissionHelper

/**
 * Dialog for requesting location permissions required for duty tracking
 */
@Composable
fun LocationPermissionDialog(
    showDialog: Boolean,
    onDismiss: () -> Unit,
    onPermissionsGranted: () -> Unit,
    onPermissionsDenied: () -> Unit
) {
    val context = LocalContext.current
    var showBackgroundPermissionDialog by remember { mutableStateOf(false) }
    
    // Launcher for basic location permissions
    val locationPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.values.all { it }
        if (allGranted) {
            // Check if we need background location permission
            val missingBackgroundPerms = LocationPermissionHelper.getMissingBackgroundPermissions(context)
            if (missingBackgroundPerms.isNotEmpty()) {
                showBackgroundPermissionDialog = true
            } else {
                onPermissionsGranted()
            }
        } else {
            onPermissionsDenied()
        }
    }
    
    // Launcher for settings (Android 11+ background location)
    val settingsLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult()
    ) { _ ->
        // Re-check permissions after returning from settings
        if (LocationPermissionHelper.hasBackgroundLocationPermission(context)) {
            onPermissionsGranted()
        } else {
            onPermissionsDenied()
        }
    }
    
    // Launcher for background location permission (Android 10 only)
    val backgroundPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.values.all { it }
        if (allGranted) {
            onPermissionsGranted()
        } else {
            onPermissionsDenied()
        }
    }
    
    if (showDialog) {
        AlertDialog(
            onDismissRequest = onDismiss,
            title = {
                Text("Location Permission Required")
            },
            text = {
                Column {
                    Text(
                        text = "PLS Travels needs location access to track your duty routes for:",
                        modifier = Modifier.padding(bottom = 12.dp)
                    )
                    
                    Text("• Route compliance verification")
                    Text("• Accurate mileage calculation")
                    Text("• Safety monitoring")
                    Text("• Duty performance analytics")
                    
                    Spacer(modifier = Modifier.height(12.dp))
                    
                    Text(
                        text = "Location data is only collected during active duty periods.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val missingPermissions = LocationPermissionHelper.getMissingPermissions(context)
                        if (missingPermissions.isNotEmpty()) {
                            locationPermissionLauncher.launch(missingPermissions)
                        } else {
                            onPermissionsGranted()
                        }
                    }
                ) {
                    Text("Grant Permission")
                }
            },
            dismissButton = {
                TextButton(onClick = onDismiss) {
                    Text("Cancel")
                }
            }
        )
    }
    
    // Background location permission dialog
    if (showBackgroundPermissionDialog) {
        AlertDialog(
            onDismissRequest = { 
                showBackgroundPermissionDialog = false
                onPermissionsDenied()
            },
            title = {
                Text("Background Location Permission")
            },
            text = {
                Column {
                    Text(
                        text = "🚖 Background Location Required",
                        style = MaterialTheme.typography.titleMedium,
                        modifier = Modifier.padding(bottom = 8.dp)
                    )
                    
                    Text(
                        text = "PLS Travels collects location data in the background ONLY during active duty periods to:",
                        modifier = Modifier.padding(bottom = 8.dp)
                    )
                    
                    Text("• Track routes for compliance verification")
                    Text("• Calculate accurate trip distances")
                    Text("• Ensure driver safety monitoring")
                    Text("• Generate duty performance reports")
                    
                    Spacer(modifier = Modifier.height(12.dp))
                    
                    Text(
                        text = "⚠️ Location tracking stops immediately when you end your duty.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.primary
                    )
                    
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    val instructionText = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                        "You'll be taken to Settings. Select 'Location' → 'App permissions' → 'Allow all the time'"
                    } else {
                        "Select 'Allow all the time' in the permission dialog"
                    }
                    
                    Text(
                        text = instructionText,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                        textAlign = TextAlign.Center,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        showBackgroundPermissionDialog = false
                        val missingBackgroundPerms = LocationPermissionHelper.getMissingBackgroundPermissions(context)
                        if (missingBackgroundPerms.isNotEmpty()) {
                            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                                // Android 11+: Must go to Settings
                                val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                                    data = Uri.fromParts("package", context.packageName, null)
                                }
                                settingsLauncher.launch(intent)
                            } else {
                                // Android 10: Can still use runtime permissions
                                backgroundPermissionLauncher.launch(missingBackgroundPerms)
                            }
                        } else {
                            onPermissionsGranted()
                        }
                    }
                ) {
                    Text("Continue")
                }
            },
            dismissButton = {
                TextButton(
                    onClick = { 
                        showBackgroundPermissionDialog = false
                        onPermissionsDenied()
                    }
                ) {
                    Text("Skip")
                }
            }
        )
    }
}