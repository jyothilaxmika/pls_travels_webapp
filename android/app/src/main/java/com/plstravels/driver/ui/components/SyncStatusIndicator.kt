package com.plstravels.driver.ui.components

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material.icons.filled.SyncProblem
import androidx.compose.material.icons.filled.CloudDone
import androidx.compose.material.icons.filled.CloudUpload
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * Component to display sync status with pending operations count
 */
@Composable
fun SyncStatusIndicator(
    pendingCount: Int,
    isConnected: Boolean,
    isSyncing: Boolean,
    lastSyncTime: Long?,
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null
) {
    val (backgroundColor, contentColor, icon, statusText) = when {
        !isConnected && pendingCount > 0 -> {
            val color = MaterialTheme.colorScheme.error
            Quad(color, MaterialTheme.colorScheme.onError, Icons.Default.SyncProblem, "Offline ($pendingCount pending)")
        }
        isSyncing -> {
            val color = Color(0xFF2196F3) // Blue
            Quad(color, Color.White, Icons.Default.CloudUpload, "Syncing...")
        }
        pendingCount > 0 -> {
            val color = Color(0xFFFF9800) // Orange
            Quad(color, Color.White, Icons.Default.Sync, "$pendingCount pending")
        }
        else -> {
            val color = Color(0xFF4CAF50) // Green
            Quad(color, Color.White, Icons.Default.CloudDone, "All synced")
        }
    }

    // Rotation animation for syncing state
    val infiniteTransition = rememberInfiniteTransition(label = "sync_rotation")
    val rotation by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = if (isSyncing) 360f else 0f,
        animationSpec = infiniteRepeatable(
            animation = tween(2000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "sync_rotation"
    )

    Surface(
        modifier = modifier
            .clickable { onClick?.invoke() },
        shape = RoundedCornerShape(16.dp),
        color = backgroundColor
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Icon(
                imageVector = icon,
                contentDescription = statusText,
                tint = contentColor,
                modifier = Modifier
                    .size(18.dp)
                    .rotate(if (isSyncing) rotation else 0f)
            )
            
            Text(
                text = statusText,
                color = contentColor,
                fontSize = 13.sp,
                fontWeight = FontWeight.Medium
            )
        }
    }
}

/**
 * Compact sync status with just a badge
 */
@Composable
fun CompactSyncBadge(
    pendingCount: Int,
    isConnected: Boolean,
    modifier: Modifier = Modifier
) {
    if (pendingCount > 0) {
        Box(
            modifier = modifier
                .background(
                    color = if (isConnected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                    shape = CircleShape
                )
                .size(20.dp),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = if (pendingCount > 9) "9+" else pendingCount.toString(),
                color = Color.White,
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

/**
 * Offline mode banner for full-width notifications
 */
@Composable
fun OfflineModeBanner(
    pendingCount: Int,
    onSyncClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    if (pendingCount > 0) {
        Surface(
            modifier = modifier.fillMaxWidth(),
            color = MaterialTheme.colorScheme.errorContainer,
            contentColor = MaterialTheme.colorScheme.onErrorContainer
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.SyncProblem,
                        contentDescription = "Offline mode",
                        modifier = Modifier.size(20.dp)
                    )
                    
                    Column {
                        Text(
                            text = "Working offline",
                            fontWeight = FontWeight.Medium,
                            fontSize = 14.sp
                        )
                        Text(
                            text = "$pendingCount operations will sync when connected",
                            fontSize = 12.sp
                        )
                    }
                }
                
                TextButton(
                    onClick = onSyncClick
                ) {
                    Text("View")
                }
            }
        }
    }
}

/**
 * Helper data class for component state
 */
private data class Quad<A, B, C, D>(
    val first: A,
    val second: B,
    val third: C,
    val fourth: D
)