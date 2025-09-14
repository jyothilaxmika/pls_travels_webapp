package com.plstravels.driver.service

import android.content.Context
import android.util.Log
import androidx.work.*
import com.plstravels.driver.data.repository.ConnectivityRepository
import kotlinx.coroutines.flow.first
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Centralized sync constraint management for optimal background sync behavior
 * Integrates battery optimization, network awareness, and WorkManager constraints
 */
@Singleton
class SyncConstraintManager @Inject constructor(
    private val connectivityRepository: ConnectivityRepository,
    private val networkAwareSyncService: NetworkAwareSyncService
) {
    companion object {
        private const val TAG = "SyncConstraintManager"
    }
    
    /**
     * Create optimal constraints based on sync priority and context
     */
    suspend fun createConstraintsForPriority(
        context: Context,
        priority: Int,
        reason: String
    ): Constraints {
        val batteryLevel = BatteryOptimizedSyncScheduler.getBatteryLevel(context)
        val isCharging = BatteryOptimizedSyncScheduler.isDeviceCharging(context)
        val isDozeMode = BatteryOptimizedSyncScheduler.isDozeMode(context)
        val networkRecommendations = networkAwareSyncService.getSyncRecommendations()
        
        Log.d(TAG, "Creating constraints - priority: $priority, battery: $batteryLevel%, " +
                "charging: $isCharging, doze: $isDozeMode, network: ${networkRecommendations.networkType}")
        
        return when (priority) {
            4 -> createCriticalConstraints(isCharging, networkRecommendations) // Emergency/Expedited
            3 -> createHighPriorityConstraints(batteryLevel, isCharging, networkRecommendations) // Duty operations
            2 -> createMediumPriorityConstraints(batteryLevel, isCharging, isDozeMode, networkRecommendations) // Important sync
            1 -> createLowPriorityConstraints(batteryLevel, isCharging, isDozeMode, networkRecommendations) // Periodic sync
            else -> createDefaultConstraints(networkRecommendations)
        }
    }
    
    /**
     * Critical constraints - minimal restrictions for emergency operations
     */
    private fun createCriticalConstraints(
        isCharging: Boolean,
        networkRecommendations: NetworkSyncRecommendations
    ): Constraints {
        return Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .setRequiresBatteryNotLow(false) // Allow even on low battery
            .setRequiresCharging(false)
            .setRequiresDeviceIdle(false)
            .setRequiresStorageNotLow(true)
            .build()
    }
    
    /**
     * High priority constraints - for duty operations and critical user actions
     */
    private fun createHighPriorityConstraints(
        batteryLevel: Int,
        isCharging: Boolean,
        networkRecommendations: NetworkSyncRecommendations
    ): Constraints {
        return Constraints.Builder()
            .setRequiredNetworkType(if (networkRecommendations.isMetered) NetworkType.UNMETERED else NetworkType.CONNECTED)
            .setRequiresBatteryNotLow(batteryLevel <= 10 && !isCharging) // Only restrict on very low battery
            .setRequiresCharging(false)
            .setRequiresDeviceIdle(false)
            .setRequiresStorageNotLow(true)
            .build()
    }
    
    /**
     * Medium priority constraints - for important but non-critical sync
     */
    private fun createMediumPriorityConstraints(
        batteryLevel: Int,
        isCharging: Boolean,
        isDozeMode: Boolean,
        networkRecommendations: NetworkSyncRecommendations
    ): Constraints {
        return Constraints.Builder()
            .setRequiredNetworkType(if (networkRecommendations.isMetered) NetworkType.UNMETERED else NetworkType.CONNECTED)
            .setRequiresBatteryNotLow(batteryLevel <= 20 && !isCharging)
            .setRequiresCharging(false)
            .setRequiresDeviceIdle(isDozeMode && batteryLevel <= 30) // Respect Doze on low battery
            .setRequiresStorageNotLow(true)
            .build()
    }
    
    /**
     * Low priority constraints - for periodic background sync
     */
    private fun createLowPriorityConstraints(
        batteryLevel: Int,
        isCharging: Boolean,
        isDozeMode: Boolean,
        networkRecommendations: NetworkSyncRecommendations
    ): Constraints {
        return Constraints.Builder()
            .setRequiredNetworkType(
                when {
                    networkRecommendations.isMetered -> NetworkType.UNMETERED
                    networkRecommendations.networkType == "WIFI" -> NetworkType.UNMETERED
                    else -> NetworkType.CONNECTED
                }
            )
            .setRequiresBatteryNotLow(!isCharging) // Always respect battery level when not charging
            .setRequiresCharging(false)
            .setRequiresDeviceIdle(isDozeMode) // Respect Doze mode for background sync
            .setRequiresStorageNotLow(true)
            .build()
    }
    
    /**
     * Default constraints for unknown priority levels
     */
    private fun createDefaultConstraints(networkRecommendations: NetworkSyncRecommendations): Constraints {
        return Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .setRequiresBatteryNotLow(true)
            .setRequiresCharging(false)
            .setRequiresDeviceIdle(false)
            .setRequiresStorageNotLow(true)
            .build()
    }
    
    /**
     * Create work request with optimized constraints and backoff
     */
    suspend fun createOptimizedWorkRequest(
        context: Context,
        priority: Int,
        reason: String,
        isOneTime: Boolean = true,
        intervalMinutes: Long = 15L,
        attemptCount: Int = 0
    ): WorkRequest {
        val constraints = createConstraintsForPriority(context, priority, reason)
        val backoffDelay = BatteryOptimizedSyncScheduler.calculateBackoffDelay(attemptCount)
        
        val inputData = workDataOf(
            BackgroundSyncWorker.KEY_SYNC_REASON to reason,
            BackgroundSyncWorker.KEY_PRIORITY to priority,
            "optimized" to true,
            "attempt_count" to attemptCount,
            "backoff_delay" to backoffDelay
        )
        
        return if (isOneTime) {
            val builder = OneTimeWorkRequestBuilder<BackgroundSyncWorker>()
                .setConstraints(constraints)
                .setBackoffCriteria(
                    BackoffPolicy.EXPONENTIAL,
                    backoffDelay,
                    TimeUnit.SECONDS
                )
                .setInputData(inputData)
                .addTag("optimized_sync")
            
            // Add expedited processing for high priority
            if (priority >= 3) {
                builder.setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
            }
            
            builder.build()
        } else {
            val flexInterval = BatteryOptimizedSyncScheduler.calculateFlexInterval(intervalMinutes)
            
            PeriodicWorkRequestBuilder<BackgroundSyncWorker>(
                intervalMinutes, TimeUnit.MINUTES,
                flexInterval, TimeUnit.MINUTES
            )
                .setConstraints(constraints)
                .setBackoffCriteria(
                    BackoffPolicy.EXPONENTIAL,
                    backoffDelay,
                    TimeUnit.SECONDS
                )
                .setInputData(inputData)
                .addTag("optimized_periodic_sync")
                .build()
        }
    }
    
    /**
     * Schedule sync with optimal constraints based on current conditions
     */
    suspend fun scheduleOptimizedSync(
        context: Context,
        priority: Int = 2,
        reason: String = "optimized_sync",
        immediate: Boolean = false,
        attemptCount: Int = 0
    ) {
        val shouldAllow = BatteryOptimizedSyncScheduler.shouldAllowSync(context, priority)
        
        if (!shouldAllow && priority < 3) {
            Log.d(TAG, "Sync not allowed due to device constraints - priority: $priority")
            return
        }
        
        val workRequest = createOptimizedWorkRequest(context, priority, reason, isOneTime = true, attemptCount = attemptCount)
        
        if (immediate || priority >= 3) {
            WorkManager.getInstance(context).enqueue(workRequest as OneTimeWorkRequest)
            Log.d(TAG, "Scheduled immediate optimized sync - priority: $priority, reason: $reason, attempt: $attemptCount")
        } else {
            // Schedule with delay based on current conditions and exponential backoff
            val baseDelay = if (BatteryOptimizedSyncScheduler.isDozeMode(context)) {
                15L // Delay during Doze mode
            } else {
                1L // Minimal delay for normal conditions
            }
            
            // Apply exponential backoff for retries
            val backoffMultiplier = if (attemptCount > 0) {
                kotlin.math.pow(2.0, attemptCount.toDouble()).toLong()
            } else {
                1L
            }
            val totalDelay = baseDelay * backoffMultiplier
            
            val delayedRequest = (workRequest as OneTimeWorkRequest).toBuilder()
                .setInitialDelay(totalDelay, TimeUnit.MINUTES)
                .build()
            
            WorkManager.getInstance(context).enqueue(delayedRequest)
            Log.d(TAG, "Scheduled delayed optimized sync - priority: $priority, delay: ${totalDelay}min, attempt: $attemptCount")
        }
    }
    
    /**
     * Get comprehensive sync status including all constraint factors
     */
    suspend fun getComprehensiveSyncStatus(context: Context): ComprehensiveSyncStatus {
        val isConnected = connectivityRepository.isConnected.first()
        val networkRecommendations = networkAwareSyncService.getSyncRecommendations()
        val syncScheduleInfo = BatteryOptimizedSyncScheduler.getSyncScheduleInfo(context)
        val canSyncNow = BatteryOptimizedSyncScheduler.shouldAllowSync(context, 2)
        
        return ComprehensiveSyncStatus(
            canSyncNow = canSyncNow,
            networkStatus = networkRecommendations,
            batteryStatus = syncScheduleInfo,
            overallRecommendation = when {
                !isConnected -> "No network connection"
                syncScheduleInfo.isDozeMode -> "Device in power saving mode - limited sync"
                syncScheduleInfo.batteryOptimizationActive -> "Battery optimization active - reduced sync frequency"
                networkRecommendations.isMetered -> "Metered connection - critical data only"
                canSyncNow -> "All systems ready for sync"
                else -> "Sync temporarily restricted"
            }
        )
    }
}

/**
 * Comprehensive sync status including all constraint factors
 */
data class ComprehensiveSyncStatus(
    val canSyncNow: Boolean,
    val networkStatus: NetworkSyncRecommendations,
    val batteryStatus: SyncScheduleInfo,
    val overallRecommendation: String
)