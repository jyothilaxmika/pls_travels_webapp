package com.plstravels.driver.service

import android.content.Context
import android.util.Log
import com.plstravels.driver.data.repository.CommandQueueRepository
import com.plstravels.driver.data.repository.ConnectivityRepository
import com.plstravels.driver.utils.ProdLogger
import com.plstravels.driver.utils.CrashReportingManager
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.filter
import kotlinx.coroutines.flow.first
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.math.min
import kotlin.math.pow

/**
 * Manages automatic synchronization of offline data when network becomes available
 */
@Singleton
class SyncManager @Inject constructor(
    @ApplicationContext private val context: Context,
    private val commandQueueRepository: CommandQueueRepository,
    private val connectivityRepository: ConnectivityRepository,
    private val logger: ProdLogger,
    private val crashReportingManager: CrashReportingManager
) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var syncJob: Job? = null
    private var isInitialized = false
    
    companion object {
        private const val TAG = "SyncManager"
        private const val INITIAL_RETRY_DELAY_MS = 1000L // 1 second
        private const val MAX_RETRY_DELAY_MS = 30000L // 30 seconds
        private const val BACKOFF_MULTIPLIER = 2.0
        private const val PERIODIC_SYNC_INTERVAL_MS = 300_000L // 5 minutes
        private const val CLEANUP_INTERVAL_MS = 3600_000L // 1 hour
    }
    
    /**
     * Initialize the sync manager
     */
    fun initialize() {
        if (isInitialized) {
            logger.d(TAG, "SyncManager already initialized")
            return
        }
        
        logger.logOperation(TAG, "sync_manager_initialization") {
            logger.d(TAG, "Initializing SyncManager")
            crashReportingManager.setSyncStatus("initializing")
            
            // Start monitoring connectivity changes
            startConnectivityMonitoring()
            
            // Start periodic sync for any missed commands
            startPeriodicSync()
            
            // Start periodic cleanup
            startPeriodicCleanup()
            
            isInitialized = true
            crashReportingManager.setSyncStatus("active")
            logger.i(TAG, "SyncManager initialized successfully")
        }
    }
    
    /**
     * Shutdown the sync manager
     */
    fun shutdown() {
        try {
            logger.i(TAG, "Shutting down SyncManager")
            crashReportingManager.setSyncStatus("shutting_down")
            
            syncJob?.cancel()
            scope.cancel()
            isInitialized = false
            
            crashReportingManager.setSyncStatus("inactive")
            logger.i(TAG, "SyncManager shutdown completed")
        } catch (e: Exception) {
            logger.e(TAG, "Error during SyncManager shutdown", throwable = e)
            crashReportingManager.recordSyncError("shutdown", null, 0, e)
        }
    }
    
    /**
     * Trigger immediate sync if connected
     */
    suspend fun triggerSync(): Int {
        return logger.logOperation(TAG, "trigger_immediate_sync") {
            if (!connectivityRepository.isConnected.first()) {
                logger.d(TAG, "No connectivity, skipping immediate sync")
                crashReportingManager.setSyncStatus("no_connectivity")
                return@logOperation 0
            }
            
            logger.i(TAG, "Triggering immediate sync")
            executeSync()
        }
    }
    
    /**
     * Perform full synchronization for background sync worker
     */
    suspend fun performFullSync(): BackgroundSyncResult {
        return try {
            Log.d(TAG, "Starting full sync for background worker")
            
            // Check connectivity first
            if (!connectivityRepository.isConnected.first()) {
                Log.w(TAG, "No connectivity - cannot perform sync")
                return BackgroundSyncResult.NETWORK_ERROR
            }
            
            // Execute sync and get count
            val executedCount = executeSync()
            
            // Check if there are still pending commands
            val pendingCount = commandQueueRepository.getPendingCommandCount().first()
            
            Log.d(TAG, "Full sync completed - executed: $executedCount, remaining: $pendingCount")
            
            when {
                executedCount > 0 && pendingCount == 0 -> BackgroundSyncResult.SUCCESS
                executedCount > 0 && pendingCount > 0 -> BackgroundSyncResult.PARTIAL_SUCCESS
                executedCount == 0 && pendingCount == 0 -> BackgroundSyncResult.SUCCESS
                else -> BackgroundSyncResult.FAILURE
            }
        } catch (e: Exception) {
            Log.e(TAG, "Exception during full sync", e)
            BackgroundSyncResult.FAILURE
        }
    }
    
    /**
     * Start monitoring connectivity changes and sync when connected
     */
    private fun startConnectivityMonitoring() {
        scope.launch {
            connectivityRepository.isConnected
                .distinctUntilChanged()
                .filter { it } // Only trigger on connection (not disconnection)
                .collect { isConnected ->
                    if (isConnected) {
                        Log.d(TAG, "Network connected, starting sync")
                        executeSync()
                    }
                }
        }
    }
    
    /**
     * Start periodic sync to handle any missed commands
     */
    private fun startPeriodicSync() {
        scope.launch {
            while (isActive) {
                delay(PERIODIC_SYNC_INTERVAL_MS)
                
                if (connectivityRepository.isConnected.first()) {
                    val pendingCount = commandQueueRepository.getPendingCommandCount().first()
                    if (pendingCount > 0) {
                        Log.d(TAG, "Periodic sync: $pendingCount pending commands")
                        executeSync()
                    }
                }
            }
        }
    }
    
    /**
     * Start periodic cleanup of old commands
     */
    private fun startPeriodicCleanup() {
        scope.launch {
            while (isActive) {
                delay(CLEANUP_INTERVAL_MS)
                
                try {
                    commandQueueRepository.cleanup()
                    Log.d(TAG, "Periodic cleanup completed")
                } catch (e: Exception) {
                    Log.e(TAG, "Error during periodic cleanup", e)
                }
            }
        }
    }
    
    /**
     * Execute sync with exponential backoff retry logic
     */
    private suspend fun executeSync(): Int {
        var totalExecuted = 0
        var retryDelay = INITIAL_RETRY_DELAY_MS
        var attemptCount = 0
        
        while (connectivityRepository.isConnected.first()) {
            try {
                val executed = commandQueueRepository.executeAllCommands()
                totalExecuted += executed
                
                if (executed == 0) {
                    // No more commands to execute
                    break
                }
                
                Log.d(TAG, "Sync batch completed: $executed commands executed")
                
                // Reset retry delay on successful execution
                retryDelay = INITIAL_RETRY_DELAY_MS
                attemptCount = 0
                
                // Small delay between batches to avoid overwhelming the server
                delay(500)
                
            } catch (e: Exception) {
                Log.e(TAG, "Error during sync execution", e)
                
                attemptCount++
                
                // Check if we should retry
                if (attemptCount < 3 && connectivityRepository.isConnected.first()) {
                    Log.d(TAG, "Retrying sync in ${retryDelay}ms (attempt $attemptCount)")
                    delay(retryDelay)
                    
                    // Exponential backoff
                    retryDelay = min(
                        (retryDelay * BACKOFF_MULTIPLIER).toLong(),
                        MAX_RETRY_DELAY_MS
                    )
                } else {
                    // Max retries reached or no connectivity
                    Log.w(TAG, "Stopping sync after $attemptCount attempts")
                    break
                }
            }
        }
        
        if (totalExecuted > 0) {
            Log.i(TAG, "Sync completed: $totalExecuted total commands executed")
        }
        
        return totalExecuted
    }
    
    /**
     * Get sync status information
     */
    suspend fun getSyncStatus(): SyncStatus {
        val isConnected = connectivityRepository.isConnected.first()
        val networkType = connectivityRepository.getCurrentNetworkType()
        val pendingCommandCount = commandQueueRepository.getPendingCommandCount().first()
        val isMetered = connectivityRepository.isMeteredConnection()
        
        return SyncStatus(
            isConnected = isConnected,
            networkType = networkType.name,
            pendingCommandCount = pendingCommandCount,
            isMetered = isMetered,
            lastSyncAttempt = System.currentTimeMillis()
        )
    }
    
    /**
     * Force sync even on metered connections (with user consent)
     */
    suspend fun forceSyncOnMetered(): Int {
        Log.d(TAG, "Force sync on metered connection")
        return if (connectivityRepository.hasInternetConnection()) {
            executeSync()
        } else {
            Log.w(TAG, "No internet connection for forced sync")
            0
        }
    }
}

/**
 * Data class representing current sync status
 */
data class SyncStatus(
    val isConnected: Boolean,
    val networkType: String,
    val pendingCommandCount: Int,
    val isMetered: Boolean,
    val lastSyncAttempt: Long
)

/**
 * Background sync result enumeration
 */
enum class BackgroundSyncResult {
    SUCCESS,
    PARTIAL_SUCCESS,
    FAILURE,
    NETWORK_ERROR
}