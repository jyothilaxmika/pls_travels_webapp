package com.plstravels.driver.ui.testing

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.plstravels.driver.BuildConfig

/**
 * Screen for testing crash reporting and logging functionality
 * Only available in DEBUG builds
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CrashReportingTestScreen(
    viewModel: CrashReportingTestViewModel = hiltViewModel()
) {
    // Only show in debug builds
    if (!BuildConfig.DEBUG) {
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "Crash reporting tests are only available in debug builds",
                style = MaterialTheme.typography.bodyLarge
            )
        }
        return
    }
    
    val scrollState = rememberScrollState()
    var showConfirmDialog by remember { mutableStateOf(false) }
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
            .verticalScroll(scrollState),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(
            text = "Crash Reporting & Logging Tests",
            style = MaterialTheme.typography.headlineMedium,
            modifier = Modifier.padding(bottom = 16.dp)
        )
        
        Text(
            text = "Test various crash reporting and logging features. Check Crashlytics dashboard and logs for results.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(bottom = 16.dp)
        )
        
        // Non-Fatal Exception Test
        ElevatedButton(
            onClick = { viewModel.testNonFatalException() },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Test Non-Fatal Exception")
        }
        
        // Sync Error Test
        ElevatedButton(
            onClick = { viewModel.testSyncError() },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Test Sync Error Reporting")
        }
        
        // API Error Test
        ElevatedButton(
            onClick = { viewModel.testApiError() },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Test API Error Reporting")
        }
        
        // Location Error Test
        ElevatedButton(
            onClick = { viewModel.testLocationError() },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Test Location Error Reporting")
        }
        
        // Database Error Test
        ElevatedButton(
            onClick = { viewModel.testDatabaseError() },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Test Database Error Reporting")
        }
        
        // Custom Keys Test
        ElevatedButton(
            onClick = { viewModel.testCustomKeys() },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Test Custom Keys & Context")
        }
        
        // Structured Logging Test
        ElevatedButton(
            onClick = { viewModel.testStructuredLogging() },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Test Structured Logging")
        }
        
        Divider(modifier = Modifier.padding(vertical = 8.dp))
        
        // Comprehensive Test
        Button(
            onClick = { viewModel.testAllFeatures() },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Run All Tests")
        }
        
        Divider(modifier = Modifier.padding(vertical = 8.dp))
        
        // Force Crash (Dangerous)
        OutlinedButton(
            onClick = { showConfirmDialog = true },
            colors = ButtonDefaults.outlinedButtonColors(
                contentColor = MaterialTheme.colorScheme.error
            ),
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("⚠️ Force Crash (Testing)")
        }
        
        // Status Display
        viewModel.testResults.collectAsState().value.let { results ->
            if (results.isNotEmpty()) {
                Text(
                    text = "Test Results:",
                    style = MaterialTheme.typography.titleMedium,
                    modifier = Modifier.padding(top = 16.dp)
                )
                
                results.forEach { result ->
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp)
                    ) {
                        Column(
                            modifier = Modifier.padding(12.dp)
                        ) {
                            Text(
                                text = result.testName,
                                style = MaterialTheme.typography.bodyMedium,
                                color = if (result.success) {
                                    MaterialTheme.colorScheme.primary
                                } else {
                                    MaterialTheme.colorScheme.error
                                }
                            )
                            if (result.message.isNotEmpty()) {
                                Text(
                                    text = result.message,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }
                }
            }
        }
    }
    
    // Confirmation Dialog for Force Crash
    if (showConfirmDialog) {
        AlertDialog(
            onDismissRequest = { showConfirmDialog = false },
            title = { Text("⚠️ Warning") },
            text = { 
                Text("This will force crash the app for testing crash reporting. The app will immediately close. Are you sure?")
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        showConfirmDialog = false
                        viewModel.forceCrash()
                    }
                ) {
                    Text("Yes, Crash App")
                }
            },
            dismissButton = {
                TextButton(
                    onClick = { showConfirmDialog = false }
                ) {
                    Text("Cancel")
                }
            }
        )
    }
}