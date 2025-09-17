package com.plstravels.driver.ui.location

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.plstravels.driver.utils.LocationPermissionHelper
import com.plstravels.driver.utils.LocationPermissionState
import timber.log.Timber

/**
 * Screen for handling location permissions with educational UI
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LocationPermissionScreen(
    onPermissionsGranted: () -> Unit,
    onSkip: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val locationPermissionHelper = remember { LocationPermissionHelper(context) }
    
    var permissionState by remember { mutableStateOf(locationPermissionHelper.getLocationPermissionState()) }
    var showRationale by remember { mutableStateOf(false) }
    
    // Location permissions launcher
    val locationPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.values.all { it }
        permissionState = locationPermissionHelper.getLocationPermissionState()
        
        if (allGranted || permissionState == LocationPermissionState.GRANTED_FOREGROUND_ONLY) {
            Timber.i("Location permissions granted: $permissions")
            if (permissionState == LocationPermissionState.GRANTED_ALL) {
                onPermissionsGranted()
            }
        } else {
            Timber.w("Location permissions denied: $permissions")
            showRationale = true
        }
    }
    
    // Background location permission launcher
    val backgroundLocationPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        permissionState = locationPermissionHelper.getLocationPermissionState()
        
        if (permissionState == LocationPermissionState.GRANTED_ALL) {
            Timber.i("Background location permission granted")
            onPermissionsGranted()
        } else {
            Timber.w("Background location permission denied")
            // Still allow app to continue with foreground-only permissions
            onPermissionsGranted()
        }
    }
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Location Permissions") },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer,
                    titleContentColor = MaterialTheme.colorScheme.onPrimaryContainer
                )
            )
        },
        modifier = modifier
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            
            // Header
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer
                )
            ) {
                Column(
                    modifier = Modifier.padding(20.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Icon(
                        imageVector = Icons.Default.LocationOn,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onPrimaryContainer,
                        modifier = Modifier.size(48.dp)
                    )
                    
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    Text(
                        text = "Location Access Required",
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onPrimaryContainer,
                        textAlign = TextAlign.Center
                    )
                }
            }
            
            // Status Card
            Card(
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = when (permissionState) {
                                LocationPermissionState.GRANTED_ALL -> Icons.Default.CheckCircle
                                LocationPermissionState.GRANTED_FOREGROUND_ONLY -> Icons.Default.Warning
                                LocationPermissionState.DENIED -> Icons.Default.Error
                            },
                            contentDescription = null,
                            tint = when (permissionState) {
                                LocationPermissionState.GRANTED_ALL -> MaterialTheme.colorScheme.primary
                                LocationPermissionState.GRANTED_FOREGROUND_ONLY -> MaterialTheme.colorScheme.secondary
                                LocationPermissionState.DENIED -> MaterialTheme.colorScheme.error
                            },
                            modifier = Modifier.size(24.dp)
                        )
                        
                        Spacer(modifier = Modifier.width(8.dp))
                        
                        Text(
                            text = locationPermissionHelper.getPermissionStatusMessage(),
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }
            }
            
            // Why We Need Location
            Card(
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text(
                        text = "Why do we need location access?",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                    
                    LocationBenefitItem(
                        icon = Icons.Default.Route,
                        title = "Route Tracking",
                        description = "Track your route during duties for accurate mileage calculation"
                    )
                    
                    LocationBenefitItem(
                        icon = Icons.Default.Timeline,
                        title = "Duty Verification",
                        description = "Verify duty start/end locations for fleet management"
                    )
                    
                    LocationBenefitItem(
                        icon = Icons.Default.Security,
                        title = "Driver Safety",
                        description = "Emergency location sharing and driver safety features"
                    )
                    
                    LocationBenefitItem(
                        icon = Icons.Default.Assessment,
                        title = "Accurate Reports",
                        description = "Generate accurate duty reports and earnings calculation"
                    )
                }
            }
            
            // Permission Explanation
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant
                )
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = locationPermissionHelper.getLocationPermissionExplanation(),
                        style = MaterialTheme.typography.bodyMedium,
                        lineHeight = 20.sp
                    )
                }
            }
            
            Spacer(modifier = Modifier.weight(1f))
            
            // Action Buttons
            Column(
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                when (permissionState) {
                    LocationPermissionState.DENIED -> {
                        Button(
                            onClick = {
                                if (locationPermissionHelper.shouldShowLocationPermissionRationale() && !showRationale) {
                                    showRationale = true
                                } else {
                                    locationPermissionLauncher.launch(
                                        locationPermissionHelper.getRequiredLocationPermissions()
                                    )
                                }
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Icon(Icons.Default.LocationOn, contentDescription = null)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Grant Location Access")
                        }
                    }
                    
                    LocationPermissionState.GRANTED_FOREGROUND_ONLY -> {
                        Button(
                            onClick = {
                                backgroundLocationPermissionLauncher.launch(
                                    locationPermissionHelper.getBackgroundLocationPermission()
                                )
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Icon(Icons.Default.MyLocation, contentDescription = null)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Enable Background Location")
                        }
                        
                        OutlinedButton(
                            onClick = onPermissionsGranted,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Continue with Foreground Only")
                        }
                    }
                    
                    LocationPermissionState.GRANTED_ALL -> {
                        Button(
                            onClick = onPermissionsGranted,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Icon(Icons.Default.CheckCircle, contentDescription = null)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Continue")
                        }
                    }
                }
                
                if (showRationale) {
                    OutlinedButton(
                        onClick = { locationPermissionHelper.openAppSettings() },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Icon(Icons.Default.Settings, contentDescription = null)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Open App Settings")
                    }
                }
                
                TextButton(
                    onClick = onSkip,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Skip for Now")
                }
            }
        }
    }
}

@Composable
private fun LocationBenefitItem(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    title: String,
    description: String,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier,
        verticalAlignment = Alignment.Top
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.primary,
            modifier = Modifier.size(20.dp)
        )
        
        Spacer(modifier = Modifier.width(12.dp))
        
        Column {
            Text(
                text = title,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Medium
            )
            
            Text(
                text = description,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}