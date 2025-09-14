package com.plstravels.driver.ui.duty

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.background
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.ui.draw.offset
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ExitToApp
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material3.*
import com.plstravels.driver.ui.components.ConnectivityIndicator
import com.plstravels.driver.ui.components.SyncStatusIndicator
import com.plstravels.driver.ui.components.OfflineModeBanner
import com.plstravels.driver.data.repository.ConnectivityRepository
import com.plstravels.driver.data.repository.CommandQueueRepository
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.plstravels.driver.data.models.Duty
import com.plstravels.driver.data.models.Vehicle
import com.plstravels.driver.ui.auth.AuthViewModel

/**
 * Main duty management screen for drivers
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DutyScreen(
    dutyViewModel: DutyViewModel = hiltViewModel(),
    authViewModel: AuthViewModel = hiltViewModel(),
    onLogout: () -> Unit,
    onNavigateToCamera: (com.plstravels.driver.data.models.PhotoType, Int?) -> Unit,
    onNavigateToNotifications: () -> Unit,
    onNavigateToSync: () -> Unit
) {
    val uiState by dutyViewModel.uiState.collectAsState()
    val activeDuty by dutyViewModel.activeDuty.collectAsState()
    val duties by dutyViewModel.duties.collectAsState()
    val vehicles by dutyViewModel.vehicles.collectAsState()
    val locationPermissionsGranted by dutyViewModel.locationPermissionsGranted.collectAsState()
    val showLocationPermissionDialog by dutyViewModel.showLocationPermissionDialog.collectAsState()
    val showPhotoCaptureSheet by dutyViewModel.showPhotoCaptureSheet.collectAsState()
    val currentDutyPhotos by dutyViewModel.currentDutyPhotos.collectAsState()
    val connectivityStatus by dutyViewModel.connectivityStatus.collectAsState()
    val syncStatus by dutyViewModel.syncStatus.collectAsState()
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        
        // Header with connectivity status
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "Driver Dashboard",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold
            )
            
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Connectivity indicator
                ConnectivityIndicator(
                    isConnected = connectivityStatus?.isConnected ?: false,
                    networkType = connectivityStatus?.networkType ?: ConnectivityRepository.NetworkType.NONE
                )
                
                // Sync status indicator
                SyncStatusIndicator(
                    pendingCount = syncStatus?.pendingCount ?: 0,
                    isConnected = connectivityStatus?.isConnected ?: false,
                    isSyncing = syncStatus?.isSyncing ?: false,
                    lastSyncTime = syncStatus?.lastSyncTime,
                    onClick = onNavigateToSync
                )
                
                // Notification bell with badge
                Box {
                    IconButton(onClick = onNavigateToNotifications) {
                        Icon(Icons.Default.Notifications, contentDescription = "Notifications")
                    }
                    
                    // Notification badge - in real app this would show unread count
                    Box(
                        modifier = Modifier
                            .size(8.dp)
                            .background(MaterialTheme.colorScheme.error, CircleShape)
                            .align(Alignment.TopEnd)
                            .offset(x = (-4).dp, y = 4.dp)
                    )
                }
                
                IconButton(
                    onClick = {
                        authViewModel.resetState()
                        onLogout()
                    }
                ) {
                    Icon(Icons.Default.ExitToApp, contentDescription = "Logout")
                }
            }
        }
        
        // Offline mode banner
        OfflineModeBanner(
            pendingCount = syncStatus?.pendingCount ?: 0,
            onSyncClick = onNavigateToSync,
            modifier = Modifier.padding(top = 8.dp)
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        // Location Permission Status
        if (!locationPermissionsGranted) {
            LocationPermissionCard(
                onRequestPermissions = { dutyViewModel.requestLocationPermissions() }
            )
            Spacer(modifier = Modifier.height(16.dp))
        }

        // Active Duty Section
        ActiveDutySection(
            activeDuty = activeDuty,
            vehicles = vehicles,
            uiState = uiState,
            locationPermissionsGranted = locationPermissionsGranted,
            onStartDuty = { vehicleId, odometer ->
                if (locationPermissionsGranted) {
                    dutyViewModel.startDuty(vehicleId, odometer, null)
                } else {
                    dutyViewModel.requestLocationPermissions()
                }
            },
            onEndDuty = { dutyId, odometer, revenue ->
                dutyViewModel.endDuty(dutyId, odometer, revenue, null)
            },
            onCapturePhoto = { dutyViewModel.showPhotoCaptureSheet() }
        )
        
        // Photo management section for active duty
        activeDuty?.let { duty ->
            Spacer(modifier = Modifier.height(16.dp))
            DutyPhotosSection(
                dutyId = duty.id,
                photos = currentDutyPhotos,
                onCapturePhoto = { dutyViewModel.showPhotoCaptureSheet() }
            )
            
            // Load photos for current duty
            LaunchedEffect(duty.id) {
                dutyViewModel.loadPhotosForDuty(duty.id)
            }
        }
        
        Spacer(modifier = Modifier.height(24.dp))
        
        // Recent Duties
        Text(
            text = "Recent Duties",
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Medium
        )
        
        Spacer(modifier = Modifier.height(8.dp))
        
        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(duties.take(10)) { duty ->
                DutyCard(duty = duty)
            }
        }
        
        // Error/Success Messages
        uiState.error?.let { error ->
            Spacer(modifier = Modifier.height(16.dp))
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.errorContainer
                )
            ) {
                Text(
                    text = error,
                    modifier = Modifier.padding(16.dp),
                    color = MaterialTheme.colorScheme.onErrorContainer
                )
            }
        }
        
        uiState.message?.let { message ->
            Spacer(modifier = Modifier.height(16.dp))
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer
                )
            ) {
                Text(
                    text = message,
                    modifier = Modifier.padding(16.dp),
                    color = MaterialTheme.colorScheme.onPrimaryContainer
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ActiveDutySection(
    activeDuty: Duty?,
    vehicles: List<Vehicle>,
    uiState: DutyUiState,
    locationPermissionsGranted: Boolean,
    onStartDuty: (Int, Double) -> Unit,
    onEndDuty: (Int?, Double, Double) -> Unit,
    onCapturePhoto: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (activeDuty != null) 
                MaterialTheme.colorScheme.primaryContainer 
            else 
                MaterialTheme.colorScheme.surfaceVariant
        )
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Text(
                text = if (activeDuty != null) "Active Duty" else "Start New Duty",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Medium
            )
            
            Spacer(modifier = Modifier.height(12.dp))
            
            if (activeDuty != null) {
                // Show active duty details
                Text("Vehicle: ${activeDuty.vehicle?.registrationNumber ?: "N/A"}")
                Text("Started: ${activeDuty.startTime ?: "N/A"}")
                Text("Distance: ${String.format("%.1f", activeDuty.distanceKm)} km")
                
                Spacer(modifier = Modifier.height(16.dp))
                
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedButton(
                        onClick = onCapturePhoto,
                        modifier = Modifier.weight(1f)
                    ) {
                        Icon(Icons.Default.CameraAlt, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Photo")
                    }
                    
                    Button(
                        onClick = { onEndDuty(activeDuty.id, 0.0, 0.0) },
                        enabled = !uiState.isLoading,
                        modifier = Modifier.weight(2f),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.error
                        )
                    ) {
                        Icon(Icons.Default.Stop, contentDescription = null)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("End Duty")
                    }
                }
            } else {
                // Show start duty controls
                var selectedVehicle by remember { mutableStateOf<Vehicle?>(null) }
                var startOdometer by remember { mutableStateOf("") }
                
                if (vehicles.isNotEmpty()) {
                    // Vehicle Selection Dropdown
                    var expanded by remember { mutableStateOf(false) }
                    
                    ExposedDropdownMenuBox(
                        expanded = expanded,
                        onExpandedChange = { expanded = !expanded }
                    ) {
                        OutlinedTextField(
                            value = selectedVehicle?.registrationNumber ?: "",
                            onValueChange = { },
                            readOnly = true,
                            label = { Text("Select Vehicle") },
                            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
                            modifier = Modifier
                                .fillMaxWidth()
                                .menuAnchor()
                        )
                        
                        ExposedDropdownMenu(
                            expanded = expanded,
                            onDismissRequest = { expanded = false }
                        ) {
                            vehicles.forEach { vehicle ->
                                DropdownMenuItem(
                                    text = { Text("${vehicle.registrationNumber} (${vehicle.model})") },
                                    onClick = {
                                        selectedVehicle = vehicle
                                        expanded = false
                                    }
                                )
                            }
                        }
                    }
                    
                    Spacer(modifier = Modifier.height(12.dp))
                    
                    OutlinedTextField(
                        value = startOdometer,
                        onValueChange = { startOdometer = it },
                        label = { Text("Start Odometer (km)") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    
                    Spacer(modifier = Modifier.height(16.dp))
                    
                    Button(
                        onClick = { 
                            selectedVehicle?.let { vehicle ->
                                onStartDuty(vehicle.id, startOdometer.toDoubleOrNull() ?: 0.0)
                            }
                        },
                        enabled = !uiState.isLoading && selectedVehicle != null && locationPermissionsGranted,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        if (uiState.isLoading) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                color = MaterialTheme.colorScheme.onPrimary
                            )
                        } else {
                            Icon(Icons.Default.PlayArrow, contentDescription = null)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(if (locationPermissionsGranted) "Start Duty" else "Grant Location Permission")
                        }
                    }
                    
                    if (!locationPermissionsGranted) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = "Location permission required for duty tracking",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.error,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                } else {
                    Text("No vehicles available")
                }
            }
        }
    }
}

@Composable
private fun DutyCard(duty: Duty) {
    Card(
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = duty.vehicle?.registrationNumber ?: "N/A",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Medium
                )
                
                Text(
                    text = duty.status,
                    style = MaterialTheme.typography.bodyMedium,
                    color = when (duty.status) {
                        "ACTIVE" -> MaterialTheme.colorScheme.primary
                        "COMPLETED" -> MaterialTheme.colorScheme.tertiary
                        else -> MaterialTheme.colorScheme.outline
                    }
                )
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "Distance: ${String.format("%.1f", duty.distanceKm)} km",
                    style = MaterialTheme.typography.bodyMedium
                )
                
                Text(
                    text = "Earnings: ₹${String.format("%.2f", duty.totalEarnings)}",
                    style = MaterialTheme.typography.bodyMedium
                )
            }
            
            if (duty.startTime != null) {
                Text(
                    text = "Started: ${duty.startTime}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.outline
                )
            }
        }
    }
    
    // Photo Capture Sheet
    if (showPhotoCaptureSheet) {
        val availablePhotoTypes = if (activeDuty != null) {
            // During duty - show all photo types
            listOf(
                com.plstravels.driver.data.models.PhotoType.DUTY_END,
                com.plstravels.driver.data.models.PhotoType.VEHICLE_INSPECTION,
                com.plstravels.driver.data.models.PhotoType.ODOMETER_READING,
                com.plstravels.driver.data.models.PhotoType.INCIDENT_REPORT,
                com.plstravels.driver.data.models.PhotoType.FUEL_RECEIPT,
                com.plstravels.driver.data.models.PhotoType.GENERAL
            )
        } else {
            // Before duty - show duty start photos
            dutyViewModel.getRequiredPhotosForDutyStart()
        }
        
        PhotoCaptureSheet(
            photoTypes = availablePhotoTypes,
            onPhotoTypeSelected = { photoType ->
                dutyViewModel.dismissPhotoCaptureSheet()
                onNavigateToCamera(photoType, activeDuty?.id)
            },
            onDismiss = { dutyViewModel.dismissPhotoCaptureSheet() }
        )
    }
}