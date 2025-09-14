package com.plstravels.driver.ui.duty

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ExitToApp
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.*
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
    onLogout: () -> Unit
) {
    val uiState by dutyViewModel.uiState.collectAsState()
    val activeDuty by dutyViewModel.activeDuty.collectAsState()
    val duties by dutyViewModel.duties.collectAsState()
    val vehicles by dutyViewModel.vehicles.collectAsState()
    val locationPermissionsGranted by dutyViewModel.locationPermissionsGranted.collectAsState()
    val showLocationPermissionDialog by dutyViewModel.showLocationPermissionDialog.collectAsState()
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        
        // Header with logout
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
            
            IconButton(
                onClick = {
                    authViewModel.resetState()
                    onLogout()
                }
            ) {
                Icon(Icons.Default.ExitToApp, contentDescription = "Logout")
            }
        }
        
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
            }
        )
        
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
    onEndDuty: (Int?, Double, Double) -> Unit
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
                
                Button(
                    onClick = { onEndDuty(activeDuty.id, 0.0, 0.0) },
                    enabled = !uiState.isLoading,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.error
                    )
                ) {
                    Icon(Icons.Default.Stop, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("End Duty")
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
}