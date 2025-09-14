package com.plstravels.driver.ui.duty

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.plstravels.driver.data.models.Photo
import java.io.File

/**
 * Section displaying photos for the current duty
 */
@Composable
fun DutyPhotosSection(
    dutyId: Int,
    photos: List<Photo>,
    onCapturePhoto: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Duty Photos",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Medium
                )
                
                Text(
                    text = "${photos.size} photos",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
            }
            
            Spacer(modifier = Modifier.height(12.dp))
            
            LazyRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                // Add photo button
                item {
                    AddPhotoCard(onClick = onCapturePhoto)
                }
                
                // Photo thumbnails
                items(photos) { photo ->
                    PhotoThumbnail(photo = photo)
                }
            }
            
            if (photos.isEmpty()) {
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "No photos captured yet. Tap + to add photos for this duty.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
            }
        }
    }
}

@Composable
private fun AddPhotoCard(
    onClick: () -> Unit
) {
    Card(
        onClick = onClick,
        modifier = Modifier.size(80.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant
        )
    ) {
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Icon(
                    Icons.Default.Add,
                    contentDescription = "Add Photo",
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(24.dp)
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "Add",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.primary
                )
            }
        }
    }
}

@Composable
private fun PhotoThumbnail(
    photo: Photo
) {
    Card(
        modifier = Modifier.size(80.dp)
    ) {
        Box {
            AsyncImage(
                model = File(photo.localFilePath),
                contentDescription = photo.photoType.displayName,
                modifier = Modifier
                    .fillMaxSize()
                    .clip(RoundedCornerShape(8.dp)),
                contentScale = ContentScale.Crop
            )
            
            // Photo type badge
            Card(
                modifier = Modifier
                    .align(Alignment.BottomStart)
                    .padding(4.dp),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.9f)
                )
            ) {
                Text(
                    text = getPhotoTypeBadge(photo.photoType),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onPrimary,
                    modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp)
                )
            }
            
            // Upload status indicator
            if (!photo.isUploaded) {
                Icon(
                    Icons.Default.CameraAlt,
                    contentDescription = "Not uploaded",
                    tint = MaterialTheme.colorScheme.error,
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(4.dp)
                        .size(16.dp)
                )
            }
        }
    }
}

private fun getPhotoTypeBadge(photoType: com.plstravels.driver.data.models.PhotoType): String {
    return when (photoType) {
        com.plstravels.driver.data.models.PhotoType.DUTY_START -> "START"
        com.plstravels.driver.data.models.PhotoType.DUTY_END -> "END"
        com.plstravels.driver.data.models.PhotoType.VEHICLE_INSPECTION -> "VEHICLE"
        com.plstravels.driver.data.models.PhotoType.ODOMETER_READING -> "ODO"
        com.plstravels.driver.data.models.PhotoType.INCIDENT_REPORT -> "INC"
        com.plstravels.driver.data.models.PhotoType.FUEL_RECEIPT -> "FUEL"
        com.plstravels.driver.data.models.PhotoType.GENERAL -> "GEN"
    }
}