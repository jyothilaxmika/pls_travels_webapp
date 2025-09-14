package com.plstravels.driver.utils

import android.content.Context
import com.plstravels.driver.BuildConfig
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Utility class for testing crash reporting and logging functionality
 * Only available in DEBUG builds for testing purposes
 */
@Singleton
class CrashReportingTestUtil @Inject constructor(
    @ApplicationContext private val context: Context,
    private val crashReportingManager: CrashReportingManager,
    private val logger: ProdLogger
) {
    
    companion object {
        private const val TAG = "CrashReportingTest"
    }
    
    /**
     * Test non-fatal exception reporting
     */
    fun testNonFatalException() {
        if (!BuildConfig.DEBUG) return
        
        logger.i(TAG, "Testing non-fatal exception reporting")
        
        try {
            // Create a test exception
            throw RuntimeException("Test non-fatal exception for crash reporting validation")
        } catch (e: Exception) {
            // Record the exception with additional context
            crashReportingManager.recordException(
                e,
                mapOf(
                    "test_type" to "non_fatal_exception",
                    "test_timestamp" to System.currentTimeMillis().toString(),
                    "test_context" to "crash_reporting_validation"
                )
            )
            
            logger.e(TAG, "Test non-fatal exception recorded", throwable = e)
        }
    }
    
    /**
     * Test sync error reporting
     */
    fun testSyncErrorReporting() {
        if (!BuildConfig.DEBUG) return
        
        logger.i(TAG, "Testing sync error reporting")
        
        val testException = RuntimeException("Test sync operation failure")
        
        crashReportingManager.recordSyncError(
            operation = "test_sync_operation",
            commandType = "TEST_COMMAND",
            retryCount = 3,
            throwable = testException
        )
        
        logger.e(TAG, "Test sync error recorded", throwable = testException)
    }
    
    /**
     * Test API error reporting
     */
    fun testApiErrorReporting() {
        if (!BuildConfig.DEBUG) return
        
        logger.i(TAG, "Testing API error reporting")
        
        val testException = RuntimeException("Test API call failure")
        
        crashReportingManager.recordApiError(
            endpoint = "/api/test/endpoint",
            httpStatus = 500,
            errorMessage = "Internal Server Error - Test",
            requestDuration = 2500L,
            throwable = testException
        )
        
        logger.e(TAG, "Test API error recorded", throwable = testException)
    }
    
    /**
     * Test location error reporting
     */
    fun testLocationErrorReporting() {
        if (!BuildConfig.DEBUG) return
        
        logger.i(TAG, "Testing location error reporting")
        
        val testException = RuntimeException("Test location tracking failure")
        
        crashReportingManager.recordLocationError(
            errorType = "gps_unavailable",
            dutyId = 12345,
            sessionId = "test-session-12345",
            throwable = testException
        )
        
        logger.e(TAG, "Test location error recorded", throwable = testException)
    }
    
    /**
     * Test database error reporting
     */
    fun testDatabaseErrorReporting() {
        if (!BuildConfig.DEBUG) return
        
        logger.i(TAG, "Testing database error reporting")
        
        val testException = RuntimeException("Test database operation failure")
        
        crashReportingManager.recordDatabaseError(
            operation = "insert_test_record",
            tableName = "test_table",
            throwable = testException
        )
        
        logger.e(TAG, "Test database error recorded", throwable = testException)
    }
    
    /**
     * Test custom key reporting
     */
    fun testCustomKeyReporting() {
        if (!BuildConfig.DEBUG) return
        
        logger.i(TAG, "Testing custom key reporting")
        
        // Set various context data
        crashReportingManager.setDriverContext(
            driverId = "TEST_DRIVER_123",
            vehicleId = 456,
            dutyId = 789
        )
        
        crashReportingManager.setNetworkContext(
            networkType = "WIFI",
            isMetered = false,
            isConnected = true
        )
        
        crashReportingManager.setSyncStatus(
            status = "test_sync_active",
            pendingCommandsCount = 5,
            lastSyncTime = System.currentTimeMillis()
        )
        
        logger.i(TAG, "Custom keys and context set for testing")
    }
    
    /**
     * Test structured logging
     */
    fun testStructuredLogging() {
        if (!BuildConfig.DEBUG) return
        
        logger.i(TAG, "Testing structured logging")
        
        // Test different log levels with metadata
        logger.d(TAG, "Debug message with metadata", 
            mapOf("debug_data" to "test_value", "log_level" to "debug"))
        
        logger.i(TAG, "Info message with metadata", 
            mapOf("info_data" to "test_value", "log_level" to "info"))
        
        logger.w(TAG, "Warning message with metadata", 
            mapOf("warning_data" to "test_value", "log_level" to "warning"))
        
        // Test operation logging
        logger.logOperation(TAG, "test_operation") {
            Thread.sleep(100) // Simulate some work
            "Operation completed successfully"
        }
        
        // Test API call logging
        logger.logApiCall(TAG, "/api/test", "POST") {
            Thread.sleep(50) // Simulate API call
            "API call successful"
        }
        
        logger.i(TAG, "Structured logging test completed")
    }
    
    /**
     * Test all crash reporting features
     */
    fun testAllFeatures() {
        if (!BuildConfig.DEBUG) return
        
        logger.i(TAG, "Starting comprehensive crash reporting test")
        
        testCustomKeyReporting()
        testStructuredLogging()
        testNonFatalException()
        testSyncErrorReporting()
        testApiErrorReporting()
        testLocationErrorReporting()
        testDatabaseErrorReporting()
        
        logger.i(TAG, "Comprehensive crash reporting test completed")
    }
    
    /**
     * Force a crash for testing (DEBUG ONLY)
     */
    fun forceCrash() {
        if (!BuildConfig.DEBUG) return
        
        logger.w(TAG, "⚠️ Force crash requested for testing")
        crashReportingManager.forceCrash()
    }
}