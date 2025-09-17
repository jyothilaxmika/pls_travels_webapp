package com.plstravels.driver.ui.location

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
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.plstravels.driver.data.database.entity.LocationEntity
import com.plstravels.driver.data.repository.LocationStats
import java.text.SimpleDateFormat
import java.util.*

/**
 * Location dashboard screen showing tracking statistics and recent locations
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LocationDashboardScreen(
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: LocationViewModel = hiltViewModel()
) {
    val uiState = viewModel.uiState
    val locationStats by viewModel.locationStats.collectAsState()
    val recentLocations by viewModel.getRecentLocations().collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Location Tracking") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(
                        onClick = { viewModel.syncLocations() },
                        enabled = !uiState.isSyncing
                    ) {
                        if (uiState.isSyncing) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                strokeWidth = 2.dp
                            )
                        } else {
                            Icon(Icons.Default.Sync, contentDescription = "Sync")
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer,
                    titleContentColor = MaterialTheme.colorScheme.onPrimaryContainer,
                    navigationIconContentColor = MaterialTheme.colorScheme.onPrimaryContainer,
                    actionIconContentColor = MaterialTheme.colorScheme.onPrimaryContainer
                )
            )
        },
        modifier = modifier
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            
            // Location Statistics Cards
            item {
                LocationStatsCards(
                    stats = locationStats,
                    onSync = { viewModel.syncLocations() },
                    onCleanup = { viewModel.cleanupOldLocations() },
                    isSyncing = uiState.isSyncing,
                    isCleaningUp = uiState.isCleaningUp
                )
            }
            
            // Recent Locations Header
            item {
                Text(
                    text = "Recent Locations (Last 20)",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.padding(vertical = 8.dp)
                )
            }
            
            // Recent Locations List
            if (recentLocations.isEmpty()) {
                item {
                    Card(
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(24.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Icon(
                                imageVector = Icons.Default.LocationOff,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.size(48.dp)
                            )
                            
                            Spacer(modifier = Modifier.height(8.dp))
                            
                            Text(
                                text = "No location data yet",
                                style = MaterialTheme.typography.bodyLarge,
                                textAlign = TextAlign.Center,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            
                            Text(
                                text = "Start a duty to begin location tracking",
                                style = MaterialTheme.typography.bodyMedium,
                                textAlign = TextAlign.Center,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
            } else {
                items(recentLocations) { location ->
                    LocationCard(location = location)
                }
            }
        }
    }
    
    // Show messages
    LaunchedEffect(uiState.message, uiState.error) {
        // Handle snackbar or toast messages here
        // This would typically use a SnackbarHostState
    }
}

@Composable
private fun LocationStatsCards(
    stats: LocationStats,
    onSync: () -> Unit,
    onCleanup: () -> Unit,
    isSyncing: Boolean,
    isCleaningUp: Boolean,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier,
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // Today's Stats
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.primaryContainer
            )
        ) {
            Column(
                modifier = Modifier.padding(16.dp)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.Today,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                    
                    Spacer(modifier = Modifier.width(8.dp))
                    
                    Text(
                        text = "Today's Tracking",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Medium,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                }
                
                Spacer(modifier = Modifier.height(8.dp))
                
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column {
                        Text(
                            text = "${stats.totalLocationsToday}",
                            style = MaterialTheme.typography.headlineMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
                        Text(
                            text = "Locations Recorded",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.8f)
                        )
                    }
                    
                    Column(
                        horizontalAlignment = Alignment.End
                    ) {
                        Text(
                            text = "${String.format("%.1f", stats.averageAccuracy)}m",
                            style = MaterialTheme.typography.headlineMedium,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
                        Text(
                            text = "Avg Accuracy",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.8f)
                        )
                    }
                }
            }
        }
        
        // Sync Status
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
                    Column {
                        Text(
                            text = "Unsynced Locations",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Medium
                        )
                        
                        Text(
                            text = "${stats.unsyncedCount} pending sync",
                            style = MaterialTheme.typography.bodyMedium,
                            color = if (stats.unsyncedCount > 0) 
                                MaterialTheme.colorScheme.secondary 
                            else MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    
                    Button(
                        onClick = onSync,
                        enabled = !isSyncing && stats.unsyncedCount > 0
                    ) {
                        if (isSyncing) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(16.dp),
                                strokeWidth = 2.dp
                            )
                        } else {
                            Icon(
                                imageVector = Icons.Default.CloudUpload,
                                contentDescription = null,
                                modifier = Modifier.size(16.dp)
                            )
                        }
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Sync Now")
                    }
                }
            }
        }
        
        // Last Location
        if (stats.lastLocationTime != null) {
            Card(
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.Schedule,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary
                    )
                    
                    Spacer(modifier = Modifier.width(12.dp))
                    
                    Column {
                        Text(
                            text = "Last Location Update",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Medium
                        )
                        
                        Text(
                            text = SimpleDateFormat("MMM dd, HH:mm:ss", Locale.getDefault())
                                .format(Date(stats.lastLocationTime)),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
        
        // Cleanup Action
        OutlinedButton(
            onClick = onCleanup,
            enabled = !isCleaningUp,
            modifier = Modifier.fillMaxWidth()
        ) {
            if (isCleaningUp) {
                CircularProgressIndicator(
                    modifier = Modifier.size(16.dp),
                    strokeWidth = 2.dp
                )
            } else {
                Icon(
                    imageVector = Icons.Default.CleaningServices,
                    contentDescription = null,
                    modifier = Modifier.size(16.dp)
                )
            }
            Spacer(modifier = Modifier.width(8.dp))
            Text("Clean Up Old Data")
        }
    }
}

@Composable
private fun LocationCard(
    location: LocationEntity,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(
                modifier = Modifier.weight(1f)
            ) {
                Text(
                    text = "${String.format("%.6f", location.latitude)}, ${String.format("%.6f", location.longitude)}",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium
                )
                
                Text(
                    text = SimpleDateFormat("MMM dd, HH:mm:ss", Locale.getDefault())
                        .format(Date(location.timestamp)),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        text = "±${location.accuracy.toInt()}m",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.secondary
                    )
                    
                    if (location.speed > 0) {
                        Text(
                            text = "${String.format("%.1f", location.speed * 3.6f)}km/h",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.secondary
                        )
                    }
                }
            }
            
            // Sync Status
            Icon(
                imageVector = if (location.isSynced) Icons.Default.CheckCircle else Icons.Default.Schedule,
                contentDescription = if (location.isSynced) "Synced" else "Pending sync",
                tint = if (location.isSynced) 
                    MaterialTheme.colorScheme.primary 
                else MaterialTheme.colorScheme.secondary,
                modifier = Modifier.size(20.dp)
            )
        }
    }
}