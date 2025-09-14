package com.plstravels.driver.ui.sync

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.plstravels.driver.ui.components.ConnectivityIndicator
import com.plstravels.driver.ui.components.SyncStatusIndicator
import java.text.SimpleDateFormat
import java.util.*

/**
 * Screen showing detailed sync status and pending operations
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SyncStatusScreen(
    onBack: () -> Unit,
    viewModel: SyncStatusViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    val syncStatus by viewModel.syncStatus.collectAsState()
    val pendingCommands by viewModel.pendingCommands.collectAsState()
    
    LaunchedEffect(Unit) {
        viewModel.refreshData()
    }
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Sync Status") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(
                        onClick = { viewModel.refreshData() }
                    ) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh")
                    }
                }
            )
        }
    ) { paddingValues ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            item {
                SyncStatusOverview(
                    syncStatus = syncStatus,
                    onForceSyncClick = { viewModel.forceSync() }
                )
            }
            
            item {
                ConnectivityStatus(syncStatus = syncStatus)
            }
            
            if (pendingCommands.isNotEmpty()) {
                item {
                    Text(
                        text = "Pending Operations (${pendingCommands.size})",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                }
                
                items(pendingCommands) { command ->
                    PendingCommandItem(command = command)
                }
            } else {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 32.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "All operations synced ✅",
                            style = MaterialTheme.typography.bodyLarge,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun SyncStatusOverview(
    syncStatus: SyncStatusUiState,
    onForceSyncClick: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                text = "Sync Overview",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            
            SyncStatusIndicator(
                pendingCount = syncStatus.pendingCount,
                isConnected = syncStatus.isConnected,
                isSyncing = syncStatus.isSyncing,
                lastSyncTime = syncStatus.lastSyncTime,
                modifier = Modifier.fillMaxWidth()
            )
            
            if (syncStatus.lastSyncTime != null) {
                Text(
                    text = "Last sync: ${formatTimestamp(syncStatus.lastSyncTime)}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            
            if (syncStatus.pendingCount > 0) {
                Button(
                    onClick = onForceSyncClick,
                    modifier = Modifier.fillMaxWidth(),
                    enabled = syncStatus.isConnected && !syncStatus.isSyncing
                ) {
                    Text(if (syncStatus.isSyncing) "Syncing..." else "Force Sync Now")
                }
            }
        }
    }
}

@Composable
private fun ConnectivityStatus(
    syncStatus: SyncStatusUiState
) {
    Card(
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(
                text = "Network Status",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            
            ConnectivityIndicator(
                isConnected = syncStatus.isConnected,
                networkType = syncStatus.networkType,
                modifier = Modifier.fillMaxWidth()
            )
            
            if (syncStatus.isMetered) {
                Text(
                    text = "⚠️ Using metered connection (cellular data)",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error
                )
            }
        }
    }
}

@Composable
private fun PendingCommandItem(
    command: PendingCommandUiState
) {
    Card(
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = command.typeDisplayName,
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.Medium
                )
                
                Text(
                    text = formatTimestamp(command.timestamp),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            
            if (command.retryCount > 0) {
                Text(
                    text = "Retries: ${command.retryCount}/${command.maxRetries}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error
                )
            }
            
            if (command.lastError != null) {
                Text(
                    text = "Error: ${command.lastError}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error
                )
            }
        }
    }
}

private fun formatTimestamp(timestamp: Long): String {
    val format = SimpleDateFormat("MMM dd, HH:mm", Locale.getDefault())
    return format.format(Date(timestamp))
}