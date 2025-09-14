package com.plstravels.driver.service

import android.content.Context
import android.util.Log
import androidx.work.*
import kotlinx.coroutines.flow.first
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Unified sync orchestrator that centralizes all background sync scheduling
 * Replaces multiple overlapping schedulers to prevent conflicts and ensure optimal behavior
 */
@Singleton
class UnifiedSyncOrchestrator @Inject constructor(
    private val syncConstraintManager: SyncConstraintManager,
    private val networkAwareSyncService: NetworkAwareSyncService
) {
    companion object {
        private const val TAG = "UnifiedSyncOrchestrator"
        
        // Single unified work names to prevent overlapping schedulers
        const val UNIFIED_PERIODIC_SYNC_WORK = "unified_periodic_sync"
        const val UNIFIED_IMMEDIATE_SYNC_WORK = "unified_immediate_sync"
        
        // Default sync parameters
        private const val DEFAULT_SYNC_INTERVAL_MINUTES = 15L
        private const val DEFAULT_FLEX_INTERVAL_MINUTES = 5L
        
        // Priority levels for different sync types
        const val PRIORITY_CRITICAL = 4      // Emergency operations
        const val PRIORITY_HIGH = 3          // Duty operations, user actions
        const val PRIORITY_MEDIUM = 2        // Important background sync
        const val PRIORITY_LOW = 1           // Periodic maintenance sync
    }
    
    /**
     * Start unified sync orchestration with optimal scheduling
     * This replaces all other sync schedulers
     */
    suspend fun startUnifiedSync(context: Context) {
        Log.d(TAG, "Starting unified sync orchestration")
        
        // Cancel any existing overlapping work from old schedulers
        cancelAllConflictingWork(context)
        
        // Set orchestrator reference for network service callbacks
        networkAwareSyncService.setUnifiedOrchestrator(this)
        
        // Start network monitoring for adaptive sync behavior
        networkAwareSyncService.startNetworkAwareSync(context)
        
        // Schedule the unified periodic sync with optimal constraints
        scheduleUnifiedPeriodicSync(context)
        
        Log.d(TAG, "Unified sync orchestration started successfully")
    }
    
    /**
     * Stop all sync orchestration
     */
    fun stopUnifiedSync(context: Context) {
        Log.d(TAG, "Stopping unified sync orchestration")
        
        networkAwareSyncService.stopNetworkAwareSync()
        cancelAllSyncWork(context)
        
        Log.d(TAG, "Unified sync orchestration stopped")
    }
    
    /**
     * Schedule unified periodic sync with optimal constraints
     */
    private suspend fun scheduleUnifiedPeriodicSync(context: Context) {
        Log.d(TAG, "Scheduling unified periodic sync")
        
        // Get network recommendations for optimal interval
        val networkRecommendations = networkAwareSyncService.getSyncRecommendations()
        val syncInterval = networkRecommendations.recommendedSyncIntervalMinutes
        val flexInterval = BatteryOptimizedSyncScheduler.calculateFlexInterval(syncInterval)
        
        // Create optimized work request using constraint manager
        val workRequest = syncConstraintManager.createOptimizedWorkRequest(
            context = context,
            priority = PRIORITY_LOW,
            reason = "unified_periodic",
            isOneTime = false,
            intervalMinutes = syncInterval
        ) as PeriodicWorkRequest
        
        // Update the work with unified naming and tags
        val unifiedWorkRequest = workRequest.toBuilder()
            .addTag("unified_sync")
            .addTag("periodic")
            .build()
        
        // Enqueue with REPLACE policy to ensure only one periodic sync
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            UNIFIED_PERIODIC_SYNC_WORK,
            ExistingPeriodicWorkPolicy.REPLACE,
            unifiedWorkRequest
        )
        
        Log.d(TAG, "Unified periodic sync scheduled - interval: ${syncInterval}min, flex: ${flexInterval}min")
    }
    
    /**
     * Schedule immediate sync with appropriate priority
     */
    suspend fun scheduleImmediateSync(
        context: Context,
        priority: Int = PRIORITY_MEDIUM,
        reason: String = "immediate_sync"
    ) {
        Log.d(TAG, "Scheduling immediate sync - priority: $priority, reason: $reason")
        
        // Check if sync is allowed based on current conditions
        if (priority < PRIORITY_HIGH && !BatteryOptimizedSyncScheduler.shouldAllowSync(context, priority)) {
            Log.d(TAG, "Immediate sync blocked by device constraints - priority: $priority")
            return
        }
        
        // Create optimized immediate sync request
        val workRequest = syncConstraintManager.createOptimizedWorkRequest(
            context = context,
            priority = priority,
            reason = reason,
            isOneTime = true
        ) as OneTimeWorkRequest
        
        // Update with unified naming and tags
        val unifiedWorkRequest = workRequest.toBuilder()
            .addTag("unified_sync")
            .addTag("immediate")
            .addTag("priority_$priority")
            .build()
        
        // Use REPLACE policy to prevent queue buildup
        WorkManager.getInstance(context).enqueueUniqueWork(
            "${UNIFIED_IMMEDIATE_SYNC_WORK}_$priority",
            ExistingWorkPolicy.REPLACE,
            unifiedWorkRequest
        )
        
        Log.d(TAG, "Immediate sync scheduled successfully")
    }
    
    /**
     * Schedule expedited sync for critical operations
     */
    suspend fun scheduleExpeditedSync(
        context: Context,
        reason: String = "critical_operation"
    ) {
        Log.d(TAG, "Scheduling expedited sync for: $reason")
        
        scheduleImmediateSync(context, PRIORITY_CRITICAL, reason)
    }
    
    /**
     * Update sync schedule based on changed conditions
     */
    suspend fun updateSyncSchedule(context: Context, trigger: String = "condition_change") {
        Log.d(TAG, "Updating sync schedule due to: $trigger")
        
        // Get current comprehensive status
        val syncStatus = syncConstraintManager.getComprehensiveSyncStatus(context)
        
        Log.d(TAG, "Current sync status: ${syncStatus.overallRecommendation}")
        
        // Reschedule periodic sync with updated constraints
        scheduleUnifiedPeriodicSync(context)
        
        // If conditions are optimal and we have pending data, schedule immediate sync
        if (syncStatus.canSyncNow && syncStatus.networkStatus.allowSync) {
            scheduleImmediateSync(context, PRIORITY_MEDIUM, "optimal_conditions")
        }
    }
    
    /**
     * Handle network connectivity changes
     */
    suspend fun handleNetworkChange(context: Context, isConnected: Boolean) {
        if (isConnected) {
            Log.d(TAG, "Network connected - updating sync schedule")
            updateSyncSchedule(context, "network_connected")
            scheduleImmediateSync(context, PRIORITY_MEDIUM, "connectivity_restored")
        } else {
            Log.d(TAG, "Network disconnected - optimizing for offline")
            // Reschedule with more conservative constraints
            scheduleUnifiedPeriodicSync(context)
        }
    }
    
    /**
     * Handle battery state changes
     */
    suspend fun handleBatteryChange(context: Context) {
        Log.d(TAG, "Battery state changed - updating sync schedule")
        updateSyncSchedule(context, "battery_change")
    }
    
    /**
     * Get unified sync status for monitoring
     */
    suspend fun getUnifiedSyncStatus(context: Context): UnifiedSyncStatus {
        val comprehensiveStatus = syncConstraintManager.getComprehensiveSyncStatus(context)
        val workInfos = WorkManager.getInstance(context)
            .getWorkInfosForUniqueWork(UNIFIED_PERIODIC_SYNC_WORK)
            .get()
        
        val isPeriodicSyncActive = workInfos.any { 
            it.state == WorkInfo.State.RUNNING || it.state == WorkInfo.State.ENQUEUED 
        }
        
        return UnifiedSyncStatus(
            isPeriodicSyncActive = isPeriodicSyncActive,
            comprehensiveStatus = comprehensiveStatus,
            lastSyncUpdate = System.currentTimeMillis()
        )
    }
    
    /**
     * Cancel all conflicting work from old schedulers
     */
    private fun cancelAllConflictingWork(context: Context) {
        val workManager = WorkManager.getInstance(context)
        
        // Cancel work from old schedulers that might conflict
        val conflictingWorkNames = listOf(
            "background_sync",
            "intelligent_periodic_sync", 
            "bandwidth_aware_sync",
            BackgroundSyncWorker.WORK_NAME
        )
        
        conflictingWorkNames.forEach { workName ->
            try {
                workManager.cancelUniqueWork(workName)
                Log.d(TAG, "Cancelled conflicting work: $workName")
            } catch (e: Exception) {
                Log.w(TAG, "Could not cancel work: $workName", e)
            }
        }
        
        // Cancel by conflicting tags
        val conflictingTags = listOf(
            "periodic_sync",
            "intelligent_sync", 
            "bandwidth_aware_sync",
            "immediate_sync"
        )
        
        conflictingTags.forEach { tag ->
            try {
                workManager.cancelAllWorkByTag(tag)
                Log.d(TAG, "Cancelled work by tag: $tag")
            } catch (e: Exception) {
                Log.w(TAG, "Could not cancel work by tag: $tag", e)
            }
        }
    }
    
    /**
     * Cancel all unified sync work
     */
    private fun cancelAllSyncWork(context: Context) {
        val workManager = WorkManager.getInstance(context)
        
        workManager.cancelUniqueWork(UNIFIED_PERIODIC_SYNC_WORK)
        workManager.cancelAllWorkByTag("unified_sync")
        
        Log.d(TAG, "All unified sync work cancelled")
    }
}

/**
 * Unified sync status information
 */
data class UnifiedSyncStatus(
    val isPeriodicSyncActive: Boolean,
    val comprehensiveStatus: ComprehensiveSyncStatus,
    val lastSyncUpdate: Long
)