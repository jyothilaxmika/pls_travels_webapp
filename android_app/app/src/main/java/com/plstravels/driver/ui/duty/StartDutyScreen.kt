package com.plstravels.driver.ui.duty

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.plstravels.driver.data.database.entity.VehicleEntity
import com.plstravels.driver.utils.PhotoCaptureHelper
import timber.log.Timber
import java.io.File

/**
 * Screen for starting a duty
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StartDutyScreen(
    onDutyStarted: () -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: DutyViewModel = hiltViewModel()
) {
    val context = LocalContext.current
    val uiState = viewModel.uiState
    val availableVehicles by viewModel.availableVehicles.collectAsState()
    
    // Form state
    var selectedVehicle by remember { mutableStateOf<VehicleEntity?>(null) }
    var startOdometer by remember { mutableStateOf("") }
    var startFuelLevel by remember { mutableStateOf("") }
    var photoUri by remember { mutableStateOf<String?>(null) }
    var photoFile by remember { mutableStateOf<File?>(null) }
    var notes by remember { mutableStateOf("") }
    var showVehicleDialog by remember { mutableStateOf(false) }
    
    // Photo capture helper
    val photoCaptureHelper = remember { PhotoCaptureHelper(context) }
    
    // Validation errors
    var odometerError by remember { mutableStateOf<String?>(null) }
    var fuelError by remember { mutableStateOf<String?>(null) }

    // Camera launcher
    val cameraLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicture()
    ) { success ->
        if (success && photoFile != null) {
            photoUri = photoFile?.absolutePath
            Timber.i("Photo captured: $photoUri")
        } else {
            Timber.w("Photo capture failed or cancelled")
            photoFile = null
            photoUri = null
        }
    }

    // Navigate on successful duty start
    LaunchedEffect(uiState.dutyStarted) {
        if (uiState.dutyStarted) {
            onDutyStarted()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Start Duty") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { paddingValues ->
        LazyColumn(
            modifier = modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Instructions
            item {
                Card(
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer
                    )
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp)
                    ) {
                        Text(
                            text = "Starting Your Duty",
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Medium,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
                        Text(
                            text = "Select your vehicle, enter current readings, and take a photo to begin your duty.",
                            fontSize = 14.sp,
                            color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.8f),
                            modifier = Modifier.padding(top = 4.dp)
                        )
                    }
                }
            }

            // Vehicle Selection
            item {
                Card {
                    Column(
                        modifier = Modifier.padding(16.dp)
                    ) {
                        Text(
                            text = "Select Vehicle",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Medium,
                            modifier = Modifier.padding(bottom = 8.dp)
                        )
                        
                        OutlinedButton(
                            onClick = { showVehicleDialog = true },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Icon(Icons.Default.DirectionsCar, contentDescription = null)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                selectedVehicle?.let { "${it.registrationNumber} - ${it.model}" } 
                                    ?: "Choose Vehicle"
                            )
                        }
                    }
                }
            }

            // Odometer Reading
            item {
                Card {
                    Column(
                        modifier = Modifier.padding(16.dp)
                    ) {
                        Text(
                            text = "Current Odometer Reading (km)",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Medium,
                            modifier = Modifier.padding(bottom = 8.dp)
                        )
                        
                        OutlinedTextField(
                            value = startOdometer,
                            onValueChange = { value ->
                                if (value.isEmpty() || value.matches(Regex("^\\d+(\\.\\d*)?$"))) {
                                    startOdometer = value
                                    odometerError = null
                                    
                                    // Validate odometer
                                    if (value.isNotEmpty()) {
                                        val reading = value.toDoubleOrNull()
                                        if (reading != null) {
                                            odometerError = viewModel.validateOdometer(
                                                reading, 
                                                selectedVehicle?.currentOdometer
                                            )
                                        }
                                    }
                                }
                            },
                            label = { Text("Odometer Reading") },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                            modifier = Modifier.fillMaxWidth(),
                            isError = odometerError != null,
                            supportingText = odometerError?.let { { Text(it) } },
                            trailingIcon = {
                                Icon(Icons.Default.Speed, contentDescription = "Odometer")
                            }
                        )
                        
                        selectedVehicle?.currentOdometer?.let { current ->
                            Text(
                                text = "Previous reading: ${current.toInt()} km",
                                fontSize = 12.sp,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                                modifier = Modifier.padding(top = 4.dp)
                            )
                        }
                    }
                }
            }

            // Fuel Level
            item {
                Card {
                    Column(
                        modifier = Modifier.padding(16.dp)
                    ) {
                        Text(
                            text = "Current Fuel Level (%)",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Medium,
                            modifier = Modifier.padding(bottom = 8.dp)
                        )
                        
                        OutlinedTextField(
                            value = startFuelLevel,
                            onValueChange = { value ->
                                if (value.isEmpty() || value.matches(Regex("^\\d+(\\.\\d*)?$"))) {
                                    startFuelLevel = value
                                    fuelError = null
                                    
                                    // Validate fuel level
                                    if (value.isNotEmpty()) {
                                        val level = value.toDoubleOrNull()
                                        if (level != null) {
                                            fuelError = viewModel.validateFuelLevel(level)
                                        }
                                    }
                                }
                            },
                            label = { Text("Fuel Level") },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                            modifier = Modifier.fillMaxWidth(),
                            isError = fuelError != null,
                            supportingText = fuelError?.let { { Text(it) } },
                            trailingIcon = {
                                Icon(Icons.Default.LocalGasStation, contentDescription = "Fuel")
                            }
                        )
                    }
                }
            }

            // Photo Capture
            item {
                Card {
                    Column(
                        modifier = Modifier.padding(16.dp)
                    ) {
                        Text(
                            text = "Vehicle Photo",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Medium,
                            modifier = Modifier.padding(bottom = 8.dp)
                        )
                        
                        Text(
                            text = "Take a photo of the vehicle and dashboard showing odometer and fuel level",
                            fontSize = 14.sp,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                            modifier = Modifier.padding(bottom = 12.dp)
                        )
                        
                        Button(
                            onClick = {
                                try {
                                    val (file, uri) = photoCaptureHelper.createStartDutyImageFile()
                                    photoFile = file
                                    cameraLauncher.launch(uri)
                                } catch (e: Exception) {
                                    Timber.e(e, "Error creating photo file")
                                    // TODO: Show error message to user
                                }
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Icon(Icons.Default.CameraAlt, contentDescription = null)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(if (photoUri != null) "Photo Captured ✓" else "Take Photo")
                        }
                        
                        // Show photo info if captured
                        photoFile?.let { file ->
                            if (file.exists()) {
                                Text(
                                    text = "Photo: ${file.name} (${String.format("%.1f", photoCaptureHelper.getFileSizeInMB(file.absolutePath))} MB)",
                                    fontSize = 12.sp,
                                    color = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.padding(top = 4.dp)
                                )
                            }
                        }
                    }
                }
            }

            // Notes (Optional)
            item {
                Card {
                    Column(
                        modifier = Modifier.padding(16.dp)
                    ) {
                        Text(
                            text = "Notes (Optional)",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Medium,
                            modifier = Modifier.padding(bottom = 8.dp)
                        )
                        
                        OutlinedTextField(
                            value = notes,
                            onValueChange = { notes = it },
                            label = { Text("Additional notes") },
                            modifier = Modifier.fillMaxWidth(),
                            minLines = 2,
                            maxLines = 4
                        )
                    }
                }
            }

            // Error/Success Messages
            uiState.error?.let { error ->
                item {
                    Card(
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.errorContainer
                        )
                    ) {
                        Text(
                            text = error,
                            color = MaterialTheme.colorScheme.onErrorContainer,
                            modifier = Modifier.padding(16.dp)
                        )
                    }
                }
            }

            uiState.message?.let { message ->
                item {
                    Card(
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.secondaryContainer
                        )
                    ) {
                        Text(
                            text = message,
                            color = MaterialTheme.colorScheme.onSecondaryContainer,
                            modifier = Modifier.padding(16.dp)
                        )
                    }
                }
            }

            // Start Duty Button
            item {
                val canStartDuty = selectedVehicle != null &&
                        startOdometer.isNotEmpty() &&
                        startFuelLevel.isNotEmpty() &&
                        odometerError == null &&
                        fuelError == null &&
                        !uiState.isLoading

                Button(
                    onClick = {
                        selectedVehicle?.let { vehicle ->
                            viewModel.startDuty(
                                vehicleId = vehicle.id,
                                startOdometer = startOdometer.toDouble(),
                                startFuelLevel = startFuelLevel.toDouble(),
                                photoUrl = photoUri,
                                latitude = null, // TODO: Add location services
                                longitude = null,
                                notes = notes.takeIf { it.isNotBlank() }
                            )
                        }
                    },
                    enabled = canStartDuty,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    if (uiState.isLoading) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(20.dp),
                            color = MaterialTheme.colorScheme.onPrimary
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                    }
                    Text("Start Duty")
                }
            }
        }
    }

    // Vehicle Selection Dialog
    if (showVehicleDialog) {
        VehicleSelectionDialog(
            vehicles = availableVehicles,
            onVehicleSelected = { vehicle ->
                selectedVehicle = vehicle
                showVehicleDialog = false
            },
            onDismiss = { showVehicleDialog = false }
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun VehicleSelectionDialog(
    vehicles: List<VehicleEntity>,
    onVehicleSelected: (VehicleEntity) -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Select Vehicle") },
        text = {
            LazyColumn {
                items(vehicles) { vehicle ->
                    Card(
                        onClick = { onVehicleSelected(vehicle) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp)
                    ) {
                        Column(
                            modifier = Modifier.padding(16.dp)
                        ) {
                            Text(
                                text = vehicle.registrationNumber,
                                fontWeight = FontWeight.Medium
                            )
                            Text(
                                text = "${vehicle.manufacturer} ${vehicle.model} (${vehicle.year})",
                                fontSize = 14.sp,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                            )
                            Text(
                                text = "Odometer: ${vehicle.currentOdometer?.toInt() ?: "Unknown"} km",
                                fontSize = 12.sp,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                            )
                        }
                    }
                }
                
                if (vehicles.isEmpty()) {
                    item {
                        Text(
                            text = "No vehicles available",
                            modifier = Modifier.padding(16.dp)
                        )
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}