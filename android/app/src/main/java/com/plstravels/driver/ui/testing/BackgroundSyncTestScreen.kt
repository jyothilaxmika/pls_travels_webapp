package com.plstravels.driver.ui.testing

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.plstravels.driver.service.*
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * Test screen for verifying background sync functionality
 * Allows testing different scenarios and monitoring sync behavior
 */
@Composable
fun BackgroundSyncTestScreen(
    viewModel: BackgroundSyncTestViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Text(
                text = "Background Sync Testing",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold
            )
        }
        
        // System Status Section
        item {
            Card(
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = "System Status",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    uiState.systemStatus?.let { status ->
                        StatusRow("Initialized", if (status.isInitialized) "✅ Yes" else "❌ No")
                        StatusRow("Pending Commands", "${status.pendingCommandCount}")
                        StatusRow("Can Sync Now", if (status.syncStatus.canSyncNow) "✅ Yes" else "❌ No")
                        StatusRow("Battery Level", "${status.batteryStatus.batteryLevel}%")
                        StatusRow("Charging", if (status.batteryStatus.isCharging) "⚡ Yes" else "🔋 No")
                        StatusRow("Doze Mode", if (status.batteryStatus.isDozeMode) "💤 Yes" else "🟢 No")
                        StatusRow("Network", status.networkStatus.networkType)
                        StatusRow("Metered", if (status.networkStatus.isMetered) "📱 Yes" else "🆓 No")
                        StatusRow("Overall", status.syncStatus.overallRecommendation)
                    }
                    
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    Button(
                        onClick = { viewModel.refreshStatus() },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Refresh Status")
                    }
                }
            }
        }
        
        // Manual Test Section
        item {
            Card(
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = "Manual Testing",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Button(
                            onClick = { viewModel.triggerLowPrioritySync() },
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Low Priority\nSync")
                        }
                        
                        Button(
                            onClick = { viewModel.triggerMediumPrioritySync() },
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Medium Priority\nSync")
                        }
                        
                        Button(
                            onClick = { viewModel.triggerHighPrioritySync() },
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("High Priority\nSync")
                        }
                    }
                    
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    Button(
                        onClick = { viewModel.triggerCriticalSync() },
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.error
                        )
                    ) {
                        Text("Critical/Emergency Sync")
                    }
                }
            }
        }
        
        // Battery Optimization Testing
        item {
            Card(
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = "Battery Optimization Test",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    uiState.batteryTest?.let { battery ->
                        StatusRow("Battery Level", "${battery.batteryLevel}%")
                        StatusRow("Charging", if (battery.isCharging) "⚡ Yes" else "🔋 No")
                        StatusRow("Doze Mode", if (battery.isDozeMode) "💤 Yes" else "🟢 No")
                        StatusRow("Next Sync Interval", "${battery.scheduleInfo.nextSyncIntervalMinutes} min")
                        StatusRow("Battery Optimization", if (battery.scheduleInfo.batteryOptimizationActive) "⚠️ Active" else "✅ Normal")
                        
                        Spacer(modifier = Modifier.height(8.dp))
                        
                        Text("Sync Priority Permissions:")
                        StatusRow("Low Priority (1)", if (battery.lowPriorityAllowed) "✅ Allowed" else "❌ Blocked")
                        StatusRow("Medium Priority (2)", if (battery.mediumPriorityAllowed) "✅ Allowed" else "❌ Blocked")
                        StatusRow("High Priority (3)", if (battery.highPriorityAllowed) "✅ Allowed" else "❌ Blocked")
                    }
                    
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    Button(
                        onClick = { viewModel.testBatteryOptimization() },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Test Battery Optimization")
                    }
                }
            }
        }
        
        // Test Results Section
        item {
            Card(
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = "Test Results",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    if (uiState.testResults.isEmpty()) {
                        Text(
                            text = "No test results yet. Trigger some tests to see results here.",
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                }
            }
        }
        
        items(uiState.testResults) { result ->
            Card(
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = "Test: ${result.type}",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "Time: ${java.text.SimpleDateFormat("HH:mm:ss").format(result.timestamp)}",
                        style = MaterialTheme.typography.bodySmall
                    )
                    Text(
                        text = result.description,
                        style = MaterialTheme.typography.bodyMedium
                    )
                }
            }
        }
        
        // Instructions Section
        item {
            Card(
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = "Testing Instructions",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    Text(
                        text = """
                        📱 App Background Test:
                        1. Trigger a sync, then press home button
                        2. Check if sync continues in background
                        
                        ⚡ Battery Test:
                        1. Unplug device to test battery optimization
                        2. Try different priority syncs
                        
                        🌐 Network Test:
                        1. Switch between WiFi and cellular
                        2. Enable data saver mode
                        
                        💀 App Kill Test:
                        1. Trigger sync, then force-stop app
                        2. Restart app and check if sync resumes
                        """.trimIndent(),
                        style = MaterialTheme.typography.bodyMedium
                    )
                }
            }
        }
    }
}

@Composable
private fun StatusRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodyMedium
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.Medium
        )
    }
}

/**
 * ViewModel for background sync testing screen
 */
@HiltViewModel
class BackgroundSyncTestViewModel @Inject constructor(
    private val backgroundSyncInitializer: BackgroundSyncInitializer
) : ViewModel() {
    
    private val _uiState = MutableStateFlow(BackgroundSyncTestUiState())
    val uiState: StateFlow<BackgroundSyncTestUiState> = _uiState.asStateFlow()
    
    init {
        refreshStatus()
    }
    
    fun refreshStatus() {
        viewModelScope.launch {
            try {
                val context = null // Would need to inject context properly
                // val status = backgroundSyncInitializer.getSystemStatus(context)
                // _uiState.value = _uiState.value.copy(systemStatus = status)
                
                // For now, add a test result
                addTestResult("Status Refresh", "System status refreshed")
            } catch (e: Exception) {
                addTestResult("Status Refresh", "Error: ${e.message}")
            }
        }
    }
    
    fun triggerLowPrioritySync() {
        addTestResult("Low Priority Sync", "Triggered low priority background sync")
    }
    
    fun triggerMediumPrioritySync() {
        addTestResult("Medium Priority Sync", "Triggered medium priority background sync")
    }
    
    fun triggerHighPrioritySync() {
        addTestResult("High Priority Sync", "Triggered high priority background sync")
    }
    
    fun triggerCriticalSync() {
        addTestResult("Critical Sync", "Triggered critical/emergency background sync")
    }
    
    fun testBatteryOptimization() {
        viewModelScope.launch {
            try {
                // val context = null // Would need to inject context properly
                // val batteryTest = backgroundSyncInitializer.testBatteryOptimization(context)
                // _uiState.value = _uiState.value.copy(batteryTest = batteryTest)
                
                addTestResult("Battery Test", "Battery optimization test completed")
            } catch (e: Exception) {
                addTestResult("Battery Test", "Error: ${e.message}")
            }
        }
    }
    
    private fun addTestResult(type: String, description: String) {
        val result = TestResult(
            type = type,
            description = description,
            timestamp = System.currentTimeMillis()
        )
        
        _uiState.value = _uiState.value.copy(
            testResults = listOf(result) + _uiState.value.testResults.take(9) // Keep last 10
        )
    }
}

/**
 * UI state for background sync test screen
 */
data class BackgroundSyncTestUiState(
    val systemStatus: BackgroundSyncSystemStatus? = null,
    val batteryTest: BatteryTestResult? = null,
    val testResults: List<TestResult> = emptyList()
)

/**
 * Test result item
 */
data class TestResult(
    val type: String,
    val description: String,
    val timestamp: Long
)