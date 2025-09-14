package com.plstravels.driver.ui.camera

import androidx.camera.view.PreviewView
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.hilt.navigation.compose.hiltViewModel
import com.google.accompanist.permissions.ExperimentalPermissionsApi
import com.google.accompanist.permissions.rememberPermissionState
import com.google.accompanist.permissions.isGranted
import com.plstravels.driver.data.models.PhotoType
import com.plstravels.driver.utils.CameraPermissionHelper

/**
 * Camera screen for capturing duty photos
 */
@OptIn(ExperimentalPermissionsApi::class)
@Composable
fun CameraScreen(
    photoType: PhotoType,
    dutyId: Int? = null,
    onPhotoCapture: (String) -> Unit,
    onCancel: () -> Unit,
    cameraViewModel: CameraViewModel = hiltViewModel()
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val uiState by cameraViewModel.uiState.collectAsState()
    
    // Camera permission state
    val cameraPermissionState = rememberPermissionState(
        permission = CameraPermissionHelper.CAMERA_PERMISSION
    )
    
    var previewView by remember { mutableStateOf<PreviewView?>(null) }
    
    // Initialize camera when screen appears and permission is granted
    LaunchedEffect(previewView, cameraPermissionState.status.isGranted) {
        if (cameraPermissionState.status.isGranted) {
            previewView?.let { preview ->
                cameraViewModel.initializeCamera(lifecycleOwner, preview)
            }
        }
    }
    
    // Handle photo capture result
    LaunchedEffect(uiState.capturedPhotoPath) {
        uiState.capturedPhotoPath?.let { photoPath ->
            onPhotoCapture(photoPath)
        }
    }
    
    Box(modifier = Modifier.fillMaxSize()) {
        // Check camera permission
        if (!cameraPermissionState.status.isGranted) {
            // Show permission request UI
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                Icon(
                    Icons.Default.CameraAlt,
                    contentDescription = null,
                    modifier = Modifier.size(64.dp),
                    tint = MaterialTheme.colorScheme.outline
                )
                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    text = "Camera Permission Required",
                    style = MaterialTheme.typography.titleLarge,
                    textAlign = androidx.compose.ui.text.style.TextAlign.Center
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "This app needs camera access to capture duty photos. Please grant camera permission to continue.",
                    style = MaterialTheme.typography.bodyMedium,
                    textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
                Spacer(modifier = Modifier.height(24.dp))
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedButton(onClick = onCancel) {
                        Text("Cancel")
                    }
                    Button(
                        onClick = {
                            cameraPermissionState.launchPermissionRequest()
                        }
                    ) {
                        Text("Grant Permission")
                    }
                }
            }
        } else {
            // Camera preview
            AndroidView(
                factory = { ctx ->
                    PreviewView(ctx).also { preview ->
                        previewView = preview
                    }
                },
                modifier = Modifier.fillMaxSize()
            )
        }
        
        // Top bar with title and close button
        TopAppBar(
            title = {
                Text(
                    text = photoType.displayName,
                    color = Color.White,
                    fontWeight = FontWeight.Medium
                )
            },
            navigationIcon = {
                IconButton(onClick = onCancel) {
                    Icon(
                        Icons.Default.Close,
                        contentDescription = "Cancel",
                        tint = Color.White
                    )
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(
                containerColor = Color.Black.copy(alpha = 0.5f)
            ),
            modifier = Modifier.align(Alignment.TopCenter)
        )
        
        // Bottom controls
        Row(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(24.dp)
                .fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly,
            verticalAlignment = Alignment.CenterVertically
        ) {
            
            // Flash toggle
            IconButton(
                onClick = { cameraViewModel.toggleFlash() },
                modifier = Modifier
                    .size(48.dp)
                    .background(
                        Color.Black.copy(alpha = 0.5f),
                        CircleShape
                    )
            ) {
                Icon(
                    imageVector = if (uiState.isFlashOn) Icons.Default.FlashOn else Icons.Default.FlashOff,
                    contentDescription = "Toggle Flash",
                    tint = if (uiState.isFlashOn) Color.Yellow else Color.White,
                    modifier = Modifier.size(24.dp)
                )
            }
            
            // Capture button
            Button(
                onClick = { 
                    cameraViewModel.capturePhoto(photoType, dutyId)
                },
                enabled = !uiState.isCapturing && uiState.isCameraReady,
                modifier = Modifier
                    .size(80.dp)
                    .clip(CircleShape),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color.White,
                    contentColor = Color.Black
                )
            ) {
                if (uiState.isCapturing) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(24.dp),
                        color = Color.Black
                    )
                } else {
                    Icon(
                        Icons.Default.CameraAlt,
                        contentDescription = "Capture",
                        modifier = Modifier.size(32.dp)
                    )
                }
            }
            
            // Camera switch
            IconButton(
                onClick = { 
                    previewView?.let { preview ->
                        cameraViewModel.switchCamera(lifecycleOwner, preview)
                    }
                },
                modifier = Modifier
                    .size(48.dp)
                    .background(
                        Color.Black.copy(alpha = 0.5f),
                        CircleShape
                    )
            ) {
                Icon(
                    Icons.Default.Cameraswitch,
                    contentDescription = "Switch Camera",
                    tint = Color.White,
                    modifier = Modifier.size(24.dp)
                )
            }
        }
        
        // Photo type info card
        Card(
            modifier = Modifier
                .align(Alignment.TopCenter)
                .padding(top = 80.dp, horizontal = 16.dp),
            colors = CardDefaults.cardColors(
                containerColor = Color.Black.copy(alpha = 0.7f)
            )
        ) {
            Text(
                text = getPhotoInstructions(photoType),
                color = Color.White,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(12.dp)
            )
        }
        
        // Error message
        uiState.error?.let { error ->
            Snackbar(
                action = {
                    TextButton(onClick = { cameraViewModel.clearError() }) {
                        Text("Dismiss")
                    }
                },
                modifier = Modifier.align(Alignment.BottomCenter)
            ) {
                Text(error)
            }
        }
    }
}

private fun getPhotoInstructions(photoType: PhotoType): String {
    return when (photoType) {
        PhotoType.DUTY_START -> "Take a clear photo to document the start of your duty"
        PhotoType.DUTY_END -> "Take a photo to document the end of your duty"
        PhotoType.VEHICLE_INSPECTION -> "Capture the vehicle's condition before starting duty"
        PhotoType.ODOMETER_READING -> "Take a clear photo of the odometer reading"
        PhotoType.INCIDENT_REPORT -> "Document the incident with a clear photo"
        PhotoType.FUEL_RECEIPT -> "Capture the fuel receipt clearly"
        PhotoType.GENERAL -> "Take a photo for duty documentation"
    }
}