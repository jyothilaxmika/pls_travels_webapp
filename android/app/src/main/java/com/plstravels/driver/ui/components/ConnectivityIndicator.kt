package com.plstravels.driver.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.Wifi
import androidx.compose.material.icons.filled.WifiOff
import androidx.compose.material.icons.filled.SignalCellularConnectedNoInternet0Bar
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.plstravels.driver.data.repository.ConnectivityRepository

/**
 * Component to display connectivity status with visual indicators
 */
@Composable
fun ConnectivityIndicator(
    isConnected: Boolean,
    networkType: ConnectivityRepository.NetworkType,
    modifier: Modifier = Modifier,
    showText: Boolean = true
) {
    val (backgroundColor, contentColor, icon, statusText) = when {
        !isConnected -> {
            val color = MaterialTheme.colorScheme.error
            Quad(color, MaterialTheme.colorScheme.onError, Icons.Default.WifiOff, "Offline")
        }
        networkType == ConnectivityRepository.NetworkType.WIFI -> {
            val color = Color(0xFF4CAF50) // Green
            Quad(color, Color.White, Icons.Default.Wifi, "WiFi")
        }
        networkType == ConnectivityRepository.NetworkType.CELLULAR -> {
            val color = Color(0xFF2196F3) // Blue
            Quad(color, Color.White, Icons.Default.SignalCellularConnectedNoInternet0Bar, "Mobile")
        }
        else -> {
            val color = MaterialTheme.colorScheme.surface
            Quad(color, MaterialTheme.colorScheme.onSurface, Icons.Default.CloudOff, "Unknown")
        }
    }

    Row(
        modifier = modifier
            .background(
                color = backgroundColor,
                shape = RoundedCornerShape(12.dp)
            )
            .padding(horizontal = 8.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Icon(
            imageVector = icon,
            contentDescription = statusText,
            tint = contentColor,
            modifier = Modifier.size(16.dp)
        )
        
        if (showText) {
            Text(
                text = statusText,
                color = contentColor,
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium
            )
        }
    }
}

/**
 * Compact connectivity status indicator for top bars
 */
@Composable
fun CompactConnectivityIndicator(
    isConnected: Boolean,
    networkType: ConnectivityRepository.NetworkType,
    modifier: Modifier = Modifier
) {
    ConnectivityIndicator(
        isConnected = isConnected,
        networkType = networkType,
        modifier = modifier,
        showText = false
    )
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