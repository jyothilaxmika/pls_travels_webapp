package com.plstravels.driver.ui.duty

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
    
    // Launcher for background location permission
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
                        text = "To track your location during duty, PLS Travels needs permission to access location in the background.",
                        modifier = Modifier.padding(bottom = 12.dp)
                    )
                    
                    Text(
                        text = "This ensures accurate route tracking even when the app is not actively open.",
                        style = MaterialTheme.typography.bodyMedium
                    )
                    
                    Spacer(modifier = Modifier.height(12.dp))
                    
                    Text(
                        text = "Select 'Allow all the time' in the next screen.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.primary,
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
                            backgroundPermissionLauncher.launch(missingBackgroundPerms)
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