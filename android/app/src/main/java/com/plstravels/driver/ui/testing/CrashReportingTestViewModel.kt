package com.plstravels.driver.ui.testing

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.plstravels.driver.utils.CrashReportingTestUtil
import com.plstravels.driver.utils.ProdLogger
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * ViewModel for crash reporting test screen
 */
@HiltViewModel
class CrashReportingTestViewModel @Inject constructor(
    private val crashReportingTestUtil: CrashReportingTestUtil,
    private val logger: ProdLogger
) : ViewModel() {
    
    companion object {
        private const val TAG = "CrashReportingTestVM"
    }
    
    private val _testResults = MutableStateFlow<List<TestResult>>(emptyList())
    val testResults: StateFlow<List<TestResult>> = _testResults.asStateFlow()
    
    /**
     * Test non-fatal exception reporting
     */
    fun testNonFatalException() {
        viewModelScope.launch {
            logger.i(TAG, "Starting non-fatal exception test")
            try {
                crashReportingTestUtil.testNonFatalException()
                addTestResult("Non-Fatal Exception", true, "Exception recorded successfully")
            } catch (e: Exception) {
                addTestResult("Non-Fatal Exception", false, "Test failed: ${e.message}")
                logger.e(TAG, "Non-fatal exception test failed", throwable = e)
            }
        }
    }
    
    /**
     * Test sync error reporting
     */
    fun testSyncError() {
        viewModelScope.launch {
            logger.i(TAG, "Starting sync error test")
            try {
                crashReportingTestUtil.testSyncErrorReporting()
                addTestResult("Sync Error", true, "Sync error recorded successfully")
            } catch (e: Exception) {
                addTestResult("Sync Error", false, "Test failed: ${e.message}")
                logger.e(TAG, "Sync error test failed", throwable = e)
            }
        }
    }
    
    /**
     * Test API error reporting
     */
    fun testApiError() {
        viewModelScope.launch {
            logger.i(TAG, "Starting API error test")
            try {
                crashReportingTestUtil.testApiErrorReporting()
                addTestResult("API Error", true, "API error recorded successfully")
            } catch (e: Exception) {
                addTestResult("API Error", false, "Test failed: ${e.message}")
                logger.e(TAG, "API error test failed", throwable = e)
            }
        }
    }
    
    /**
     * Test location error reporting
     */
    fun testLocationError() {
        viewModelScope.launch {
            logger.i(TAG, "Starting location error test")
            try {
                crashReportingTestUtil.testLocationErrorReporting()
                addTestResult("Location Error", true, "Location error recorded successfully")
            } catch (e: Exception) {
                addTestResult("Location Error", false, "Test failed: ${e.message}")
                logger.e(TAG, "Location error test failed", throwable = e)
            }
        }
    }
    
    /**
     * Test database error reporting
     */
    fun testDatabaseError() {
        viewModelScope.launch {
            logger.i(TAG, "Starting database error test")
            try {
                crashReportingTestUtil.testDatabaseErrorReporting()
                addTestResult("Database Error", true, "Database error recorded successfully")
            } catch (e: Exception) {
                addTestResult("Database Error", false, "Test failed: ${e.message}")
                logger.e(TAG, "Database error test failed", throwable = e)
            }
        }
    }
    
    /**
     * Test custom keys and context
     */
    fun testCustomKeys() {
        viewModelScope.launch {
            logger.i(TAG, "Starting custom keys test")
            try {
                crashReportingTestUtil.testCustomKeyReporting()
                addTestResult("Custom Keys", true, "Custom keys and context set successfully")
            } catch (e: Exception) {
                addTestResult("Custom Keys", false, "Test failed: ${e.message}")
                logger.e(TAG, "Custom keys test failed", throwable = e)
            }
        }
    }
    
    /**
     * Test structured logging
     */
    fun testStructuredLogging() {
        viewModelScope.launch {
            logger.i(TAG, "Starting structured logging test")
            try {
                crashReportingTestUtil.testStructuredLogging()
                addTestResult("Structured Logging", true, "Structured logging test completed")
            } catch (e: Exception) {
                addTestResult("Structured Logging", false, "Test failed: ${e.message}")
                logger.e(TAG, "Structured logging test failed", throwable = e)
            }
        }
    }
    
    /**
     * Test all crash reporting features
     */
    fun testAllFeatures() {
        viewModelScope.launch {
            logger.i(TAG, "Starting comprehensive crash reporting test")
            clearTestResults()
            
            try {
                crashReportingTestUtil.testAllFeatures()
                addTestResult("Comprehensive Test", true, "All crash reporting features tested")
            } catch (e: Exception) {
                addTestResult("Comprehensive Test", false, "Test failed: ${e.message}")
                logger.e(TAG, "Comprehensive test failed", throwable = e)
            }
        }
    }
    
    /**
     * Force crash for testing
     */
    fun forceCrash() {
        logger.w(TAG, "⚠️ Force crash requested - app will terminate immediately")
        crashReportingTestUtil.forceCrash()
    }
    
    /**
     * Add a test result to the list
     */
    private fun addTestResult(testName: String, success: Boolean, message: String) {
        val currentResults = _testResults.value.toMutableList()
        currentResults.add(
            TestResult(
                testName = testName,
                success = success,
                message = message,
                timestamp = System.currentTimeMillis()
            )
        )
        _testResults.value = currentResults
        
        logger.i(TAG, "Test result added: $testName - ${if (success) "SUCCESS" else "FAILED"}")
    }
    
    /**
     * Clear all test results
     */
    private fun clearTestResults() {
        _testResults.value = emptyList()
    }
}

/**
 * Data class representing a test result
 */
data class TestResult(
    val testName: String,
    val success: Boolean,
    val message: String,
    val timestamp: Long
)