package com.plstravels.driver.utils

import android.os.Build
import android.util.Log
import com.google.firebase.crashlytics.FirebaseCrashlytics
import com.plstravels.driver.BuildConfig
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Enhanced logging configuration with structured logging and crash reporting integration
 * Provides consistent logging across the app with production-ready features
 */
@Singleton
class LoggingConfig @Inject constructor(
    private val crashReportingManager: CrashReportingManager
) {
    
    companion object {
        private const val TAG = "LoggingConfig"
        
        // Log levels
        const val LEVEL_VERBOSE = 2
        const val LEVEL_DEBUG = 3
        const val LEVEL_INFO = 4
        const val LEVEL_WARN = 5
        const val LEVEL_ERROR = 6
        const val LEVEL_ASSERT = 7
        
        // Production log level threshold
        private val PRODUCTION_LOG_LEVEL = LEVEL_INFO
        
        // Maximum log message length
        private const val MAX_LOG_LENGTH = 4000
        
        // Common metadata keys
        const val KEY_USER_ID = "user_id"
        const val KEY_SESSION_ID = "session_id"
        const val KEY_DUTY_ID = "duty_id"
        const val KEY_VEHICLE_ID = "vehicle_id"
        const val KEY_SYNC_OPERATION = "sync_operation"
        const val KEY_NETWORK_STATE = "network_state"
        const val KEY_BATTERY_LEVEL = "battery_level"
        const val KEY_MEMORY_USAGE = "memory_usage"
        const val KEY_OPERATION_DURATION = "operation_duration_ms"
        const val KEY_ERROR_CODE = "error_code"
        const val KEY_API_ENDPOINT = "api_endpoint"
        const val KEY_HTTP_STATUS = "http_status"
    }
    
    /**
     * Initialize logging configuration
     */
    fun initialize() {
        Log.i(TAG, "Initializing enhanced logging system")
        
        // Set device and app context for crash reporting
        crashReportingManager.setCustomKeys(mapOf(
            "app_version" to BuildConfig.VERSION_NAME,
            "app_version_code" to BuildConfig.VERSION_CODE.toString(),
            "device_model" to "${Build.MANUFACTURER} ${Build.MODEL}",
            "android_version" to Build.VERSION.RELEASE,
            "api_level" to Build.VERSION.SDK_INT.toString(),
            "build_type" to BuildConfig.BUILD_TYPE
        ))
        
        Log.i(TAG, "Enhanced logging system initialized (Level: ${getLogLevelName(getEffectiveLogLevel())})")
    }
    
    /**
     * Get effective log level based on build type
     */
    private fun getEffectiveLogLevel(): Int {
        return if (BuildConfig.DEBUG) {
            LEVEL_VERBOSE
        } else {
            PRODUCTION_LOG_LEVEL
        }
    }
    
    /**
     * Check if log level should be output
     */
    fun shouldLog(level: Int): Boolean {
        return level >= getEffectiveLogLevel()
    }
    
    /**
     * Enhanced verbose logging with metadata
     */
    fun v(tag: String, message: String, metadata: Map<String, String> = emptyMap(), throwable: Throwable? = null) {
        if (shouldLog(LEVEL_VERBOSE)) {
            val formattedMessage = formatLogMessage(message, metadata)
            logToConsole(Log.VERBOSE, tag, formattedMessage, throwable)
            logToCrashlytics(LEVEL_VERBOSE, tag, formattedMessage, metadata, throwable)
        }
    }
    
    /**
     * Enhanced debug logging with metadata
     */
    fun d(tag: String, message: String, metadata: Map<String, String> = emptyMap(), throwable: Throwable? = null) {
        if (shouldLog(LEVEL_DEBUG)) {
            val formattedMessage = formatLogMessage(message, metadata)
            logToConsole(Log.DEBUG, tag, formattedMessage, throwable)
            logToCrashlytics(LEVEL_DEBUG, tag, formattedMessage, metadata, throwable)
        }
    }
    
    /**
     * Enhanced info logging with metadata
     */
    fun i(tag: String, message: String, metadata: Map<String, String> = emptyMap(), throwable: Throwable? = null) {
        if (shouldLog(LEVEL_INFO)) {
            val formattedMessage = formatLogMessage(message, metadata)
            logToConsole(Log.INFO, tag, formattedMessage, throwable)
            logToCrashlytics(LEVEL_INFO, tag, formattedMessage, metadata, throwable)
        }
    }
    
    /**
     * Enhanced warning logging with metadata
     */
    fun w(tag: String, message: String, metadata: Map<String, String> = emptyMap(), throwable: Throwable? = null) {
        val formattedMessage = formatLogMessage(message, metadata)
        logToConsole(Log.WARN, tag, formattedMessage, throwable)
        logToCrashlytics(LEVEL_WARN, tag, formattedMessage, metadata, throwable)
    }
    
    /**
     * Enhanced error logging with metadata
     */
    fun e(tag: String, message: String, metadata: Map<String, String> = emptyMap(), throwable: Throwable? = null) {
        val formattedMessage = formatLogMessage(message, metadata)
        logToConsole(Log.ERROR, tag, formattedMessage, throwable)
        logToCrashlytics(LEVEL_ERROR, tag, formattedMessage, metadata, throwable)
        
        // Report non-fatal errors to Crashlytics for production monitoring
        throwable?.let { 
            crashReportingManager.recordException(it, metadata + mapOf(
                "log_tag" to tag,
                "log_message" to message
            ))
        }
    }
    
    /**
     * Log operation with timing
     */
    inline fun <T> logOperation(
        tag: String, 
        operation: String, 
        metadata: Map<String, String> = emptyMap(),
        block: () -> T
    ): T {
        val startTime = System.currentTimeMillis()
        d(tag, "Starting operation: $operation", metadata)
        
        return try {
            val result = block()
            val duration = System.currentTimeMillis() - startTime
            i(tag, "Operation completed: $operation", metadata + mapOf(
                KEY_OPERATION_DURATION to duration.toString()
            ))
            result
        } catch (e: Exception) {
            val duration = System.currentTimeMillis() - startTime
            e(tag, "Operation failed: $operation", metadata + mapOf(
                KEY_OPERATION_DURATION to duration.toString()
            ), e)
            throw e
        }
    }
    
    /**
     * Log API call with timing and response details
     */
    inline fun <T> logApiCall(
        tag: String,
        endpoint: String,
        method: String = "GET",
        metadata: Map<String, String> = emptyMap(),
        block: () -> T
    ): T {
        val startTime = System.currentTimeMillis()
        val apiMetadata = metadata + mapOf(
            KEY_API_ENDPOINT to endpoint,
            "http_method" to method
        )
        
        d(tag, "API call started: $method $endpoint", apiMetadata)
        
        return try {
            val result = block()
            val duration = System.currentTimeMillis() - startTime
            i(tag, "API call succeeded: $method $endpoint", apiMetadata + mapOf(
                KEY_OPERATION_DURATION to duration.toString(),
                "status" to "success"
            ))
            result
        } catch (e: Exception) {
            val duration = System.currentTimeMillis() - startTime
            e(tag, "API call failed: $method $endpoint", apiMetadata + mapOf(
                KEY_OPERATION_DURATION to duration.toString(),
                "status" to "error",
                KEY_ERROR_CODE to e.javaClass.simpleName
            ), e)
            throw e
        }
    }
    
    /**
     * Format log message with metadata
     */
    private fun formatLogMessage(message: String, metadata: Map<String, String>): String {
        return if (metadata.isEmpty()) {
            message
        } else {
            val metadataString = metadata.entries.joinToString(", ") { "${it.key}=${it.value}" }
            "$message [$metadataString]"
        }
    }
    
    /**
     * Log to Android console with length limitation
     */
    private fun logToConsole(priority: Int, tag: String, message: String, throwable: Throwable?) {
        val chunks = if (message.length > MAX_LOG_LENGTH) {
            message.chunked(MAX_LOG_LENGTH)
        } else {
            listOf(message)
        }
        
        chunks.forEachIndexed { index, chunk ->
            val chunkTag = if (chunks.size > 1) "$tag-${index + 1}" else tag
            when {
                throwable != null -> Log.println(priority, chunkTag, "$chunk\n${Log.getStackTraceString(throwable)}")
                else -> Log.println(priority, chunkTag, chunk)
            }
        }
    }
    
    /**
     * Log to Firebase Crashlytics for remote monitoring
     */
    private fun logToCrashlytics(level: Int, tag: String, message: String, metadata: Map<String, String>, throwable: Throwable?) {
        try {
            // Set custom keys for this log entry
            metadata.forEach { (key, value) ->
                crashReportingManager.setCustomKey(key, value)
            }
            
            // Log to Crashlytics with proper format
            val logMessage = "${getLogLevelName(level)}/$tag: $message"
            crashReportingManager.log(logMessage)
            
        } catch (e: Exception) {
            // Fail silently to avoid logging loops
            Log.w(TAG, "Failed to log to Crashlytics", e)
        }
    }
    
    /**
     * Get human-readable log level name
     */
    private fun getLogLevelName(level: Int): String {
        return when (level) {
            LEVEL_VERBOSE -> "VERBOSE"
            LEVEL_DEBUG -> "DEBUG"
            LEVEL_INFO -> "INFO"
            LEVEL_WARN -> "WARN"
            LEVEL_ERROR -> "ERROR"
            LEVEL_ASSERT -> "ASSERT"
            else -> "UNKNOWN"
        }
    }
    
    /**
     * Create context metadata for current state
     */
    fun createContextMetadata(
        userId: String? = null,
        sessionId: String? = null,
        dutyId: Int? = null,
        vehicleId: Int? = null,
        networkState: String? = null
    ): Map<String, String> {
        val metadata = mutableMapOf<String, String>()
        
        userId?.let { metadata[KEY_USER_ID] = it }
        sessionId?.let { metadata[KEY_SESSION_ID] = it }
        dutyId?.let { metadata[KEY_DUTY_ID] = it.toString() }
        vehicleId?.let { metadata[KEY_VEHICLE_ID] = it.toString() }
        networkState?.let { metadata[KEY_NETWORK_STATE] = it }
        
        return metadata.toMap()
    }
}