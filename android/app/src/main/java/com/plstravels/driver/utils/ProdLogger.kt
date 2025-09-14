package com.plstravels.driver.utils

import javax.inject.Inject
import javax.inject.Singleton

/**
 * Production-ready logger wrapper that provides enhanced logging capabilities
 * with crash reporting integration and structured metadata support
 */
@Singleton
class ProdLogger @Inject constructor(
    private val loggingConfig: LoggingConfig
) {
    
    /**
     * Verbose logging - only in debug builds
     */
    fun v(tag: String, message: String, metadata: Map<String, String> = emptyMap(), throwable: Throwable? = null) {
        loggingConfig.v(tag, message, metadata, throwable)
    }
    
    /**
     * Debug logging - only in debug builds
     */
    fun d(tag: String, message: String, metadata: Map<String, String> = emptyMap(), throwable: Throwable? = null) {
        loggingConfig.d(tag, message, metadata, throwable)
    }
    
    /**
     * Info logging - visible in production
     */
    fun i(tag: String, message: String, metadata: Map<String, String> = emptyMap(), throwable: Throwable? = null) {
        loggingConfig.i(tag, message, metadata, throwable)
    }
    
    /**
     * Warning logging - visible in production
     */
    fun w(tag: String, message: String, metadata: Map<String, String> = emptyMap(), throwable: Throwable? = null) {
        loggingConfig.w(tag, message, metadata, throwable)
    }
    
    /**
     * Error logging - visible in production with crash reporting
     */
    fun e(tag: String, message: String, metadata: Map<String, String> = emptyMap(), throwable: Throwable? = null) {
        loggingConfig.e(tag, message, metadata, throwable)
    }
    
    /**
     * Log timed operation with automatic timing
     */
    inline fun <T> logOperation(
        tag: String, 
        operation: String, 
        metadata: Map<String, String> = emptyMap(),
        block: () -> T
    ): T = loggingConfig.logOperation(tag, operation, metadata, block)
    
    /**
     * Log API call with automatic timing and context
     */
    inline fun <T> logApiCall(
        tag: String,
        endpoint: String,
        method: String = "GET",
        metadata: Map<String, String> = emptyMap(),
        block: () -> T
    ): T = loggingConfig.logApiCall(tag, endpoint, method, metadata, block)
    
    /**
     * Create context metadata for current app state
     */
    fun createContextMetadata(
        userId: String? = null,
        sessionId: String? = null,
        dutyId: Int? = null,
        vehicleId: Int? = null,
        networkState: String? = null
    ): Map<String, String> = loggingConfig.createContextMetadata(userId, sessionId, dutyId, vehicleId, networkState)
    
    /**
     * Convenience method for sync operation logging
     */
    fun logSyncOperation(
        tag: String,
        operation: String,
        commandType: String? = null,
        retryCount: Int = 0,
        metadata: Map<String, String> = emptyMap(),
        throwable: Throwable? = null
    ) {
        val syncMetadata = metadata + mapOf(
            LoggingConfig.KEY_SYNC_OPERATION to operation,
            "retry_count" to retryCount.toString()
        ).let { map ->
            commandType?.let { map + ("command_type" to it) } ?: map
        }
        
        when (throwable) {
            null -> i(tag, "Sync operation: $operation", syncMetadata)
            else -> e(tag, "Sync operation failed: $operation", syncMetadata, throwable)
        }
    }
    
    /**
     * Convenience method for API call logging
     */
    fun logApiCall(
        tag: String,
        endpoint: String,
        method: String = "GET",
        httpStatus: Int? = null,
        duration: Long? = null,
        metadata: Map<String, String> = emptyMap(),
        throwable: Throwable? = null
    ) {
        val apiMetadata = metadata + mapOf(
            LoggingConfig.KEY_API_ENDPOINT to endpoint,
            "http_method" to method
        ).let { map ->
            var result = map
            httpStatus?.let { result = result + (LoggingConfig.KEY_HTTP_STATUS to it.toString()) }
            duration?.let { result = result + (LoggingConfig.KEY_OPERATION_DURATION to it.toString()) }
            result
        }
        
        when (throwable) {
            null -> {
                val status = when {
                    httpStatus != null && httpStatus >= 200 && httpStatus < 300 -> "success"
                    httpStatus != null -> "http_error"
                    else -> "completed"
                }
                i(tag, "API call $status: $method $endpoint", apiMetadata)
            }
            else -> e(tag, "API call failed: $method $endpoint", apiMetadata, throwable)
        }
    }
    
    /**
     * Convenience method for location operation logging
     */
    fun logLocationOperation(
        tag: String,
        operation: String,
        dutyId: Int? = null,
        sessionId: String? = null,
        accuracy: Float? = null,
        metadata: Map<String, String> = emptyMap(),
        throwable: Throwable? = null
    ) {
        val locationMetadata = metadata.toMutableMap().apply {
            put("location_operation", operation)
            dutyId?.let { put(LoggingConfig.KEY_DUTY_ID, it.toString()) }
            sessionId?.let { put(LoggingConfig.KEY_SESSION_ID, it) }
            accuracy?.let { put("location_accuracy", it.toString()) }
        }
        
        when (throwable) {
            null -> i(tag, "Location operation: $operation", locationMetadata)
            else -> e(tag, "Location operation failed: $operation", locationMetadata, throwable)
        }
    }
    
    /**
     * Convenience method for duty operation logging
     */
    fun logDutyOperation(
        tag: String,
        operation: String,
        dutyId: Int? = null,
        vehicleId: Int? = null,
        status: String? = null,
        metadata: Map<String, String> = emptyMap(),
        throwable: Throwable? = null
    ) {
        val dutyMetadata = metadata.toMutableMap().apply {
            put("duty_operation", operation)
            dutyId?.let { put(LoggingConfig.KEY_DUTY_ID, it.toString()) }
            vehicleId?.let { put(LoggingConfig.KEY_VEHICLE_ID, it.toString()) }
            status?.let { put("duty_status", it) }
        }
        
        when (throwable) {
            null -> i(tag, "Duty operation: $operation", dutyMetadata)
            else -> e(tag, "Duty operation failed: $operation", dutyMetadata, throwable)
        }
    }
    
    /**
     * Convenience method for database operation logging
     */
    fun logDatabaseOperation(
        tag: String,
        operation: String,
        tableName: String? = null,
        recordCount: Int? = null,
        metadata: Map<String, String> = emptyMap(),
        throwable: Throwable? = null
    ) {
        val dbMetadata = metadata.toMutableMap().apply {
            put("db_operation", operation)
            tableName?.let { put("table_name", it) }
            recordCount?.let { put("record_count", it.toString()) }
        }
        
        when (throwable) {
            null -> d(tag, "Database operation: $operation", dbMetadata)
            else -> e(tag, "Database operation failed: $operation", dbMetadata, throwable)
        }
    }
}