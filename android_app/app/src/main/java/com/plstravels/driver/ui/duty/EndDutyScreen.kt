package com.plstravels.driver.ui.duty

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.plstravels.driver.data.database.entity.DutyEntity
import com.plstravels.driver.utils.PhotoCaptureHelper
import java.io.File
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.ui.platform.LocalContext
import timber.log.Timber

/**
 * Screen for ending an active duty
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EndDutyScreen(
    activeDuty: DutyEntity? = null,
    onDutyEnded: () -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: DutyViewModel = hiltViewModel()
) {
    val uiState = viewModel.uiState
    val context = LocalContext.current
    
    // Get active duty from ViewModel if not provided
    val currentActiveDuty by viewModel.activeDuty.collectAsState()
    val actualActiveDuty = activeDuty ?: currentActiveDuty
    
    // Return early if no active duty
    if (actualActiveDuty == null) {
        LaunchedEffect(Unit) {
            onBack() // Navigate back if no active duty
        }
        return
    }
    
    // Form state
    var endOdometer by remember { mutableStateOf("") }
    var endFuelLevel by remember { mutableStateOf("") }
    var totalRevenue by remember { mutableStateOf("") }
    var totalTrips by remember { mutableStateOf("") }
    var photoUri by remember { mutableStateOf<String?>(null) }
    var photoFile by remember { mutableStateOf<File?>(null) }
    var notes by remember { mutableStateOf("") }
    
    // Photo capture helper
    val photoCaptureHelper = remember { PhotoCaptureHelper(context) }
    
    // Validation errors
    var odometerError by remember { mutableStateOf<String?>(null) }
    var fuelError by remember { mutableStateOf<String?>(null) }
    var revenueError by remember { mutableStateOf<String?>(null) }
    var tripsError by remember { mutableStateOf<String?>(null) }

    // Camera launcher
    val cameraLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicture()
    ) { success ->
        if (success && photoFile != null) {
            photoUri = photoFile?.absolutePath
            Timber.i("End duty photo captured: $photoUri")
        } else {
            Timber.w("End duty photo capture failed or cancelled")
            photoFile = null
            photoUri = null
        }
    }

    // Navigate on successful duty end
    LaunchedEffect(uiState.dutyEnded) {
        if (uiState.dutyEnded) {
            onDutyEnded()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("End Duty") },
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
            // Duty Summary
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
                            text = "Ending Your Duty",
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Medium,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
                        
                        Spacer(modifier = Modifier.height(8.dp))
                        
                        Text(
                            text = "Started: ${formatDateTime(actualActiveDuty.startTime)}",
                            fontSize = 14.sp,
                            color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.8f)
                        )
                        
                        Text(
                            text = "Start Odometer: ${actualActiveDuty.startOdometer?.toInt() ?: "N/A"} km",
                            fontSize = 14.sp,
                            color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.8f)
                        )
                        
                        Text(
                            text = "Start Fuel: ${actualActiveDuty.startFuelLevel?.toInt() ?: "N/A"}%",
                            fontSize = 14.sp,
                            color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.8f)
                        )
                    }
                }
            }

            // End Odometer Reading
            item {
                Card {
                    Column(
                        modifier = Modifier.padding(16.dp)
                    ) {
                        Text(
                            text = "End Odometer Reading (km)",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Medium,
                            modifier = Modifier.padding(bottom = 8.dp)
                        )
                        
                        OutlinedTextField(
                            value = endOdometer,
                            onValueChange = { value ->
                                if (value.isEmpty() || value.matches(Regex("^\\d+(\\.\\d*)?$"))) {
                                    endOdometer = value
                                    odometerError = null
                                    
                                    // Validate odometer
                                    if (value.isNotEmpty()) {
                                        val reading = value.toDoubleOrNull()
                                        val startReading = actualActiveDuty.startOdometer
                                        if (reading != null && startReading != null) {
                                            if (reading < startReading) {
                                                odometerError = "End reading cannot be less than start reading (${startReading.toInt()} km)"
                                            } else if (reading - startReading > 800) {
                                                odometerError = "Reading difference too high: ${(reading - startReading).toInt()} km"
                                            }
                                        }
                                    }
                                }
                            },
                            label = { Text("End Odometer Reading") },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                            modifier = Modifier.fillMaxWidth(),
                            isError = odometerError != null,
                            supportingText = odometerError?.let { { Text(it) } },
                            trailingIcon = {
                                Icon(Icons.Default.Speed, contentDescription = "Odometer")
                            }
                        )
                        
                        // Show distance traveled
                        if (endOdometer.isNotEmpty() && actualActiveDuty.startOdometer != null) {
                            val endReading = endOdometer.toDoubleOrNull()
                            if (endReading != null && endReading >= actualActiveDuty.startOdometer) {
                                val distance = endReading - actualActiveDuty.startOdometer
                                Text(
                                    text = "Distance traveled: ${distance.toInt()} km",
                                    fontSize = 12.sp,
                                    color = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.padding(top = 4.dp)
                                )
                            }
                        }
                    }
                }
            }

            // End Fuel Level
            item {
                Card {
                    Column(
                        modifier = Modifier.padding(16.dp)
                    ) {
                        Text(
                            text = "End Fuel Level (%)",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Medium,
                            modifier = Modifier.padding(bottom = 8.dp)
                        )
                        
                        OutlinedTextField(
                            value = endFuelLevel,
                            onValueChange = { value ->
                                if (value.isEmpty() || value.matches(Regex("^\\d+(\\.\\d*)?$"))) {
                                    endFuelLevel = value
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
                            label = { Text("End Fuel Level") },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                            modifier = Modifier.fillMaxWidth(),
                            isError = fuelError != null,
                            supportingText = fuelError?.let { { Text(it) } },
                            trailingIcon = {
                                Icon(Icons.Default.LocalGasStation, contentDescription = "Fuel")
                            }
                        )
                        
                        // Show fuel consumed
                        if (endFuelLevel.isNotEmpty() && actualActiveDuty.startFuelLevel != null) {
                            val endLevel = endFuelLevel.toDoubleOrNull()
                            if (endLevel != null) {
                                val consumed = actualActiveDuty.startFuelLevel - endLevel
                                Text(
                                    text = "Fuel consumed: ${consumed.toInt()}%",
                                    fontSize = 12.sp,
                                    color = if (consumed >= 0) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                                    modifier = Modifier.padding(top = 4.dp)
                                )
                            }
                        }
                    }
                }
            }

            // Revenue and Trips
            item {
                Card {
                    Column(
                        modifier = Modifier.padding(16.dp)
                    ) {
                        Text(
                            text = "Trip Details (Optional)",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Medium,
                            modifier = Modifier.padding(bottom = 12.dp)
                        )
                        
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            // Total Revenue
                            OutlinedTextField(
                                value = totalRevenue,
                                onValueChange = { value ->
                                    if (value.isEmpty() || value.matches(Regex("^\\d+(\\.\\d*)?$"))) {
                                        totalRevenue = value
                                        revenueError = null
                                    }
                                },
                                label = { Text("Total Revenue (₹)") },
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                                modifier = Modifier.weight(1f),
                                isError = revenueError != null,
                                supportingText = revenueError?.let { { Text(it) } },
                                trailingIcon = {
                                    Icon(Icons.Default.AttachMoney, contentDescription = "Revenue")
                                }
                            )
                            
                            // Total Trips
                            OutlinedTextField(
                                value = totalTrips,
                                onValueChange = { value ->
                                    if (value.isEmpty() || value.matches(Regex("^\\d+$"))) {
                                        totalTrips = value
                                        tripsError = null
                                    }
                                },
                                label = { Text("Total Trips") },
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                modifier = Modifier.weight(1f),
                                isError = tripsError != null,
                                supportingText = tripsError?.let { { Text(it) } },
                                trailingIcon = {
                                    Icon(Icons.Default.DirectionsCar, contentDescription = "Trips")
                                }
                            )
                        }
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
                            text = "End Duty Photo",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Medium,
                            modifier = Modifier.padding(bottom = 8.dp)
                        )
                        
                        Text(
                            text = "Take a photo of the vehicle showing final odometer and fuel readings",
                            fontSize = 14.sp,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                            modifier = Modifier.padding(bottom = 12.dp)
                        )
                        
                        Button(
                            onClick = {
                                try {
                                    val (file, uri) = photoCaptureHelper.createEndDutyImageFile()
                                    photoFile = file
                                    cameraLauncher.launch(uri)
                                } catch (e: Exception) {
                                    Timber.e(e, "Error creating end duty photo file")
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

            // Notes
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
                            label = { Text("Additional notes about the duty") },
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

            // End Duty Button
            item {
                val canEndDuty = endOdometer.isNotEmpty() &&
                        endFuelLevel.isNotEmpty() &&
                        odometerError == null &&
                        fuelError == null &&
                        !uiState.isLoading

                Button(
                    onClick = {
                        viewModel.endDuty(
                            dutyId = actualActiveDuty.id,
                            endOdometer = endOdometer.toDouble(),
                            endFuelLevel = endFuelLevel.toDouble(),
                            totalRevenue = totalRevenue.toDoubleOrNull(),
                            totalTrips = totalTrips.toIntOrNull(),
                            photoUrl = photoUri,
                            latitude = null, // TODO: Add location services
                            longitude = null,
                            notes = notes.takeIf { it.isNotBlank() }
                        )
                    },
                    enabled = canEndDuty,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.error
                    )
                ) {
                    if (uiState.isLoading) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(20.dp),
                            color = MaterialTheme.colorScheme.onError
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                    }
                    Text("End Duty")
                }
            }
        }
    }
}

private fun formatDateTime(dateTimeString: String?): String {
    return try {
        if (dateTimeString != null) {
            val dateTime = LocalDateTime.parse(dateTimeString)
            dateTime.format(DateTimeFormatter.ofPattern("MMM dd, yyyy - hh:mm a"))
        } else {
            "Unknown"
        }
    } catch (e: Exception) {
        dateTimeString ?: "Unknown"
    }
}