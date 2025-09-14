package com.plstravels.driver.ui.duty

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.plstravels.driver.data.models.PhotoType

/**
 * Bottom sheet for selecting photo type to capture
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PhotoCaptureSheet(
    photoTypes: List<PhotoType>,
    onPhotoTypeSelected: (PhotoType) -> Unit,
    onDismiss: () -> Unit
) {
    ModalBottomSheet(
        onDismissRequest = onDismiss
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            Text(
                text = "Capture Photo",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(bottom = 16.dp)
            )
            
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(photoTypes) { photoType ->
                    PhotoTypeCard(
                        photoType = photoType,
                        onClick = { onPhotoTypeSelected(photoType) }
                    )
                }
            }
            
            Spacer(modifier = Modifier.height(16.dp))
        }
    }
}

@Composable
private fun PhotoTypeCard(
    photoType: PhotoType,
    onClick: () -> Unit
) {
    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = getPhotoTypeIcon(photoType),
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(24.dp)
            )
            
            Spacer(modifier = Modifier.width(16.dp))
            
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = photoType.displayName,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Medium
                )
                
                Text(
                    text = getPhotoTypeDescription(photoType),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
            }
            
            Icon(
                Icons.Default.ChevronRight,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
            )
        }
    }
}

private fun getPhotoTypeIcon(photoType: PhotoType) = when (photoType) {
    PhotoType.DUTY_START -> Icons.Default.PlayArrow
    PhotoType.DUTY_END -> Icons.Default.Stop
    PhotoType.VEHICLE_INSPECTION -> Icons.Default.DirectionsCar
    PhotoType.ODOMETER_READING -> Icons.Default.SpeedIcon
    PhotoType.INCIDENT_REPORT -> Icons.Default.Warning
    PhotoType.FUEL_RECEIPT -> Icons.Default.Receipt
    PhotoType.GENERAL -> Icons.Default.CameraAlt
}

private fun getPhotoTypeDescription(photoType: PhotoType) = when (photoType) {
    PhotoType.DUTY_START -> "Document the beginning of your duty shift"
    PhotoType.DUTY_END -> "Document the completion of your duty shift"
    PhotoType.VEHICLE_INSPECTION -> "Record vehicle condition before duty"
    PhotoType.ODOMETER_READING -> "Capture current odometer reading"
    PhotoType.INCIDENT_REPORT -> "Document any incidents or issues"
    PhotoType.FUEL_RECEIPT -> "Record fuel purchase receipts"
    PhotoType.GENERAL -> "General duty documentation photo"
}