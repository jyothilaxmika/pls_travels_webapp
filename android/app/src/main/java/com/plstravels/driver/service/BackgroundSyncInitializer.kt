package com.plstravels.driver.service

import android.content.Context
import android.util.Log
import com.plstravels.driver.data.repository.CommandQueueRepository
import com.plstravels.driver.utils.ProdLogger
import com.plstravels.driver.utils.CrashReportingManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Initializes and configures the background sync system on app startup
 * Ensures proper WorkManager integration and handles app lifecycle events
 */
@Singleton
class BackgroundSyncInitializer @Inject constructor(
    private val commandQueueRepository: CommandQueueRepository,
    private val syncConstraintManager: SyncConstraintManager,
    private val networkAwareSyncService: NetworkAwareSyncService,
    private val unifiedSyncOrchestrator: UnifiedSyncOrchestrator,
    private val logger: ProdLogger,
    private val crashReportingManager: CrashReportingManager
) {
    private val initScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var isInitialized = false
    
    companion object {
        private const val TAG = "BackgroundSyncInitializer"
    }
    
    /**
     * Initialize the complete background sync system
     * Call this from Application.onCreate() or MainActivity.onCreate()
     */
    suspend fun initialize(context: Context) {
        if (isInitialized) {
            logger.d(TAG, "Background sync already initialized")
            return
        }
        
        logger.logOperation(TAG, "background_sync_system_initialization") {
            logger.i(TAG, "Initializing background sync system")
            crashReportingManager.setSyncStatus("initializing")
            
            try {
                // Step 1: Initialize command queue repository (reset stuck commands)
                commandQueueRepository.initialize()
                logger.d(TAG, "✅ Command queue repository initialized")
                
                // Step 2: Start unified sync orchestration (includes network monitoring)
                unifiedSyncOrchestrator.startUnifiedSync(context)
                logger.d(TAG, "✅ Unified sync orchestration started")
                
                // Step 3: Check if there are pending commands and trigger immediate sync if needed
                val pendingCount = commandQueueRepository.getPendingCommandCount()
                if (pendingCount > 0) {
                    logger.i(TAG, "Found $pendingCount pending commands - triggering immediate sync",
                        mapOf("pending_commands" to pendingCount.toString()))
                    crashReportingManager.setSyncStatus("startup_sync_needed", pendingCount)
                    
                    unifiedSyncOrchestrator.scheduleImmediateSync(
                        context = context,
                        priority = UnifiedSyncOrchestrator.PRIORITY_MEDIUM,
                        reason = "app_startup_pending_data"
                    )
                } else {
                    crashReportingManager.setSyncStatus("initialized_clean", 0)
                }
                
                // Step 4: Log comprehensive sync status for debugging
                logSyncSystemStatus(context)
                
                isInitialized = true
                logger.i(TAG, "🎉 Background sync system initialization complete")
                
            } catch (e: Exception) {
                logger.e(TAG, "❌ Failed to initialize background sync system", throwable = e)
                crashReportingManager.recordSyncError("initialization", "background_sync_system", 0, e)
                throw e
            }
        }
    }
    
    /**
     * Shutdown the background sync system
     * Call this from Application.onTerminate() or when cleaning up
     */
    fun shutdown(context: Context) {
        try {
            logger.i(TAG, "Shutting down background sync system")
            crashReportingManager.setSyncStatus("shutting_down")
            
            // Stop unified sync orchestration (includes network monitoring)
            unifiedSyncOrchestrator.stopUnifiedSync(context)
            
            isInitialized = false
            crashReportingManager.setSyncStatus("shutdown")
            logger.i(TAG, "Background sync system shutdown complete")
            
        } catch (e: Exception) {
            logger.e(TAG, "Error during background sync shutdown", throwable = e)
            crashReportingManager.recordSyncError("shutdown", "background_sync_system", 0, e)
        }
    }
    
    /**
     * Trigger manual sync for testing purposes
     */
    suspend fun triggerManualSync(context: Context, priority: Int = 3): SyncTestResult {
        Log.i(TAG, "Triggering manual sync for testing - priority: $priority")
        
        val initialPendingCount = commandQueueRepository.getPendingCommandCount()
        
        // Schedule immediate high-priority sync
        unifiedSyncOrchestrator.scheduleImmediateSync(
            context = context,
            priority = priority,
            reason = "manual_test_sync"
        )
        
        // Get current sync status
        val syncStatus = unifiedSyncOrchestrator.getUnifiedSyncStatus(context)
        
        return SyncTestResult(
            initialPendingCount = initialPendingCount,
            syncTriggered = true,
            syncStatus = syncStatus,
            timestamp = System.currentTimeMillis()
        )
    }
    
    /**
     * Test battery optimization behavior
     */
    suspend fun testBatteryOptimization(context: Context): BatteryTestResult {
        Log.i(TAG, "Testing battery optimization behavior")
        
        val batteryLevel = BatteryOptimizedSyncScheduler.getBatteryLevel(context)
        val isCharging = BatteryOptimizedSyncScheduler.isDeviceCharging(context)
        val isDozeMode = BatteryOptimizedSyncScheduler.isDozeMode(context)
        val scheduleInfo = BatteryOptimizedSyncScheduler.getSyncScheduleInfo(context)
        
        // Test different priority levels
        val lowPriorityAllowed = BatteryOptimizedSyncScheduler.shouldAllowSync(context, 1)
        val mediumPriorityAllowed = BatteryOptimizedSyncScheduler.shouldAllowSync(context, 2)
        val highPriorityAllowed = BatteryOptimizedSyncScheduler.shouldAllowSync(context, 3)
        
        return BatteryTestResult(
            batteryLevel = batteryLevel,
            isCharging = isCharging,
            isDozeMode = isDozeMode,
            scheduleInfo = scheduleInfo,
            lowPriorityAllowed = lowPriorityAllowed,
            mediumPriorityAllowed = mediumPriorityAllowed,
            highPriorityAllowed = highPriorityAllowed
        )
    }
    
    /**
     * Test network awareness behavior
     */
    suspend fun testNetworkAwareness(context: Context): NetworkTestResult {
        Log.i(TAG, "Testing network awareness behavior")
        
        val recommendations = networkAwareSyncService.getSyncRecommendations()
        val syncPriority = networkAwareSyncService.getSyncPriority()
        val fullSyncRecommended = networkAwareSyncService.isFullSyncRecommended()
        
        return NetworkTestResult(
            recommendations = recommendations,
            syncPriority = syncPriority,
            fullSyncRecommended = fullSyncRecommended
        )
    }
    
    /**
     * Get comprehensive status for monitoring
     */
    suspend fun getSystemStatus(context: Context): BackgroundSyncSystemStatus {
        val syncStatus = unifiedSyncOrchestrator.getUnifiedSyncStatus(context)
        val pendingCommands = commandQueueRepository.getPendingCommandCount()
        val batteryTest = testBatteryOptimization(context)
        val networkTest = testNetworkAwareness(context)
        
        return BackgroundSyncSystemStatus(
            isInitialized = isInitialized,
            pendingCommandCount = pendingCommands,
            syncStatus = syncStatus,
            batteryStatus = batteryTest,
            networkStatus = networkTest,
            timestamp = System.currentTimeMillis()
        )
    }
    
    /**
     * Log comprehensive sync system status for debugging
     */
    private suspend fun logSyncSystemStatus(context: Context) {
        try {
            val status = getSystemStatus(context)
            
            Log.i(TAG, """
                📊 BACKGROUND SYNC SYSTEM STATUS:
                ├─ Initialized: ${status.isInitialized}
                ├─ Pending Commands: ${status.pendingCommandCount}
                ├─ Can Sync Now: ${status.syncStatus.canSyncNow}
                ├─ Battery Level: ${status.batteryStatus.batteryLevel}%
                ├─ Charging: ${status.batteryStatus.isCharging}
                ├─ Doze Mode: ${status.batteryStatus.isDozeMode}
                ├─ Network Type: ${status.networkStatus.recommendations.networkType}
                ├─ Metered Connection: ${status.networkStatus.recommendations.isMetered}
                ├─ Full Sync Recommended: ${status.networkStatus.fullSyncRecommended}
                └─ Overall: ${status.syncStatus.overallRecommendation}
            """.trimIndent())
            
        } catch (e: Exception) {
            Log.w(TAG, "Error logging sync system status", e)
        }
    }
}

/**
 * Result of manual sync test
 */
data class SyncTestResult(
    val initialPendingCount: Int,
    val syncTriggered: Boolean,
    val syncStatus: ComprehensiveSyncStatus,
    val timestamp: Long
)

/**
 * Result of battery optimization test
 */
data class BatteryTestResult(
    val batteryLevel: Int,
    val isCharging: Boolean,
    val isDozeMode: Boolean,
    val scheduleInfo: SyncScheduleInfo,
    val lowPriorityAllowed: Boolean,
    val mediumPriorityAllowed: Boolean,
    val highPriorityAllowed: Boolean
)

/**
 * Result of network awareness test
 */
data class NetworkTestResult(
    val recommendations: NetworkSyncRecommendations,
    val syncPriority: Int,
    val fullSyncRecommended: Boolean
)

/**
 * Complete background sync system status
 */
data class BackgroundSyncSystemStatus(
    val isInitialized: Boolean,
    val pendingCommandCount: Int,
    val syncStatus: ComprehensiveSyncStatus,
    val batteryStatus: BatteryTestResult,
    val networkStatus: NetworkTestResult,
    val timestamp: Long
)