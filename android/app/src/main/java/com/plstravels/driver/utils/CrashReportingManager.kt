package com.plstravels.driver.utils

import android.content.Context
import android.util.Log
import com.google.firebase.crashlytics.FirebaseCrashlytics
import com.plstravels.driver.BuildConfig
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Centralized crash reporting manager for Firebase Crashlytics integration
 * Handles crash reporting, custom logging, and user context management
 */
@Singleton
class CrashReportingManager @Inject constructor(
    @ApplicationContext private val context: Context
) {
    
    private val crashlytics: FirebaseCrashlytics by lazy { FirebaseCrashlytics.getInstance() }
    
    companion object {
        private const val TAG = "CrashReportingManager"
        
        // Custom keys for crash reporting
        const val KEY_USER_ID = "user_id"
        const val KEY_DRIVER_ID = "driver_id"
        const val KEY_SESSION_ID = "session_id"
        const val KEY_DUTY_ID = "duty_id"
        const val KEY_VEHICLE_ID = "vehicle_id"
        const val KEY_SYNC_STATUS = "sync_status"
        const val KEY_NETWORK_TYPE = "network_type"
        const val KEY_LOCATION_PERMISSION = "location_permission"
        const val KEY_APP_STATE = "app_state"
        const val KEY_LAST_SYNC_TIME = "last_sync_time"
        const val KEY_PENDING_COMMANDS_COUNT = "pending_commands_count"
        const val KEY_BATTERY_OPTIMIZATION = "battery_optimization"
    }
    
    /**
     * Initialize crash reporting with app context
     */
    fun initialize() {
        Log.i(TAG, "Initializing crash reporting system")
        
        try {
            // Enable crash reporting based on build type
            crashlytics.setCrashlyticsCollectionEnabled(!BuildConfig.DEBUG)
            
            // Set basic app information
            setCustomKey("build_type", BuildConfig.BUILD_TYPE)
            setCustomKey("version_name", BuildConfig.VERSION_NAME)
            setCustomKey("version_code", BuildConfig.VERSION_CODE.toString())
            
            // Initialize with default values
            setAppState("initialized")
            
            Log.i(TAG, "Crash reporting initialized successfully")
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to initialize crash reporting", e)
        }
    }
    
    /**
     * Set user identifier for crash reports
     */
    fun setUserId(userId: String?) {
        try {
            crashlytics.setUserId(userId ?: "anonymous")
            setCustomKey(KEY_USER_ID, userId ?: "anonymous")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to set user ID", e)
        }
    }
    
    /**
     * Set driver-specific context
     */
    fun setDriverContext(
        driverId: String?,
        vehicleId: Int? = null,
        dutyId: Int? = null
    ) {
        try {
            driverId?.let { 
                setCustomKey(KEY_DRIVER_ID, it)
                setUserId(it) // Also set as Firebase user ID
            }
            vehicleId?.let { setCustomKey(KEY_VEHICLE_ID, it.toString()) }
            dutyId?.let { setCustomKey(KEY_DUTY_ID, it.toString()) }
            
            Log.d(TAG, "Driver context updated: driver=$driverId, vehicle=$vehicleId, duty=$dutyId")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to set driver context", e)
        }
    }
    
    /**
     * Set current session ID
     */
    fun setSessionId(sessionId: String) {
        setCustomKey(KEY_SESSION_ID, sessionId)
    }
    
    /**
     * Set sync operation status
     */
    fun setSyncStatus(
        status: String,
        pendingCommandsCount: Int = 0,
        lastSyncTime: Long = System.currentTimeMillis()
    ) {
        try {
            setCustomKey(KEY_SYNC_STATUS, status)
            setCustomKey(KEY_PENDING_COMMANDS_COUNT, pendingCommandsCount.toString())
            setCustomKey(KEY_LAST_SYNC_TIME, lastSyncTime.toString())
        } catch (e: Exception) {
            Log.e(TAG, "Failed to set sync status", e)
        }
    }
    
    /**
     * Set network context
     */
    fun setNetworkContext(
        networkType: String,
        isMetered: Boolean = false,
        isConnected: Boolean = true
    ) {
        try {
            setCustomKey(KEY_NETWORK_TYPE, networkType)
            setCustomKey("is_metered", isMetered.toString())
            setCustomKey("is_connected", isConnected.toString())
        } catch (e: Exception) {
            Log.e(TAG, "Failed to set network context", e)
        }
    }
    
    /**
     * Set location permission status
     */
    fun setLocationPermissionStatus(hasPermission: Boolean, isBackgroundAllowed: Boolean = false) {
        try {
            setCustomKey(KEY_LOCATION_PERMISSION, hasPermission.toString())
            setCustomKey("background_location_permission", isBackgroundAllowed.toString())
        } catch (e: Exception) {
            Log.e(TAG, "Failed to set location permission status", e)
        }
    }
    
    /**
     * Set app state (foreground, background, etc.)
     */
    fun setAppState(state: String) {
        setCustomKey(KEY_APP_STATE, state)
    }
    
    /**
     * Set battery optimization status
     */
    fun setBatteryOptimizationStatus(isIgnoringOptimization: Boolean, batteryLevel: Int? = null) {
        try {
            setCustomKey(KEY_BATTERY_OPTIMIZATION, if (isIgnoringOptimization) "ignored" else "active")
            batteryLevel?.let { setCustomKey("battery_level", it.toString()) }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to set battery optimization status", e)
        }
    }
    
    /**
     * Record a non-fatal exception
     */
    fun recordException(
        throwable: Throwable,
        additionalData: Map<String, String> = emptyMap()
    ) {
        try {
            // Set additional context data
            additionalData.forEach { (key, value) ->
                setCustomKey(key, value)
            }
            
            // Record the exception
            crashlytics.recordException(throwable)
            
            Log.w(TAG, "Non-fatal exception recorded: ${throwable.message}")
            
        } catch (e: Exception) {
            Log.e(TAG, "Failed to record exception", e)
        }
    }
    
    /**
     * Record a custom exception with context
     */
    fun recordCustomException(
        message: String,
        cause: Throwable? = null,
        additionalData: Map<String, String> = emptyMap()
    ) {
        val customException = CustomException(message, cause)
        recordException(customException, additionalData)
    }
    
    /**
     * Log a custom message to crash reports
     */
    fun log(message: String) {
        try {
            crashlytics.log(message)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to log message to Crashlytics", e)
        }
    }
    
    /**
     * Set a custom key-value pair for crash reports
     */
    fun setCustomKey(key: String, value: String) {
        try {
            crashlytics.setCustomKey(key, value)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to set custom key: $key", e)
        }
    }
    
    /**
     * Set multiple custom keys at once
     */
    fun setCustomKeys(keyValuePairs: Map<String, String>) {
        keyValuePairs.forEach { (key, value) ->
            setCustomKey(key, value)
        }
    }
    
    /**
     * Record API error with detailed context
     */
    fun recordApiError(
        endpoint: String,
        httpStatus: Int?,
        errorMessage: String?,
        requestDuration: Long? = null,
        throwable: Throwable? = null
    ) {
        val metadata = mutableMapOf<String, String>().apply {
            put("api_endpoint", endpoint)
            httpStatus?.let { put("http_status", it.toString()) }
            errorMessage?.let { put("error_message", it) }
            requestDuration?.let { put("request_duration_ms", it.toString()) }
            put("error_type", "api_error")
        }
        
        val exception = throwable ?: CustomException("API Error: $errorMessage")
        recordException(exception, metadata)
    }
    
    /**
     * Record sync operation error
     */
    fun recordSyncError(
        operation: String,
        commandType: String?,
        retryCount: Int,
        throwable: Throwable
    ) {
        val metadata = mapOf(
            "sync_operation" to operation,
            "command_type" to (commandType ?: "unknown"),
            "retry_count" to retryCount.toString(),
            "error_type" to "sync_error"
        )
        
        recordException(throwable, metadata)
    }
    
    /**
     * Record location tracking error
     */
    fun recordLocationError(
        errorType: String,
        dutyId: Int?,
        sessionId: String?,
        throwable: Throwable
    ) {
        val metadata = mutableMapOf<String, String>().apply {
            put("location_error_type", errorType)
            put("error_type", "location_error")
            dutyId?.let { put(KEY_DUTY_ID, it.toString()) }
            sessionId?.let { put(KEY_SESSION_ID, it) }
        }
        
        recordException(throwable, metadata)
    }
    
    /**
     * Record database operation error
     */
    fun recordDatabaseError(
        operation: String,
        tableName: String?,
        throwable: Throwable
    ) {
        val metadata = mutableMapOf<String, String>().apply {
            put("db_operation", operation)
            put("error_type", "database_error")
            tableName?.let { put("table_name", it) }
        }
        
        recordException(throwable, metadata)
    }
    
    /**
     * Test crash reporting (for debugging only)
     */
    fun forceCrash() {
        if (BuildConfig.DEBUG) {
            Log.w(TAG, "Force crash triggered for testing")
            throw RuntimeException("Test crash triggered manually")
        }
    }
    
    /**
     * Custom exception class for structured error reporting
     */
    private class CustomException(message: String, cause: Throwable? = null) : Exception(message, cause)
}