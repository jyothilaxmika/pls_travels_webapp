package com.plstravels.driver.service

import android.content.Context
import android.os.PowerManager
import android.util.Log
import androidx.work.*
import com.plstravels.driver.utils.NetworkUtils
import java.util.concurrent.TimeUnit
import kotlin.math.min
import kotlin.math.pow

/**
 * Battery-optimized sync scheduler that adapts to device state
 * Implements intelligent backoff and Doze mode compatibility
 */
object BatteryOptimizedSyncScheduler {
    private const val TAG = "BatteryOptimizedSyncScheduler"
    
    // Battery optimization constants
    private const val LOW_BATTERY_THRESHOLD = 15 // Percentage
    private const val VERY_LOW_BATTERY_THRESHOLD = 5 // Percentage
    
    // Sync interval adjustments based on battery level
    private const val NORMAL_SYNC_INTERVAL_MINUTES = 15L
    private const val LOW_BATTERY_SYNC_INTERVAL_MINUTES = 30L
    private const val VERY_LOW_BATTERY_SYNC_INTERVAL_MINUTES = 60L
    
    // Doze mode intervals (Android 6+ optimization)
    private const val DOZE_MODE_SYNC_INTERVAL_MINUTES = 45L
    
    // Exponential backoff configuration
    private const val INITIAL_BACKOFF_SECONDS = 30L
    private const val MAX_BACKOFF_SECONDS = 900L // 15 minutes max
    private const val BACKOFF_MULTIPLIER = 2.0
    
    /**
     * Schedule intelligent periodic sync based on device state
     */
    fun scheduleIntelligentPeriodicSync(context: Context) {
        val batteryLevel = getBatteryLevel(context)
        val isCharging = isDeviceCharging(context)
        val isDozeMode = isDozeMode(context)
        
        val syncInterval = calculateOptimalSyncInterval(batteryLevel, isCharging, isDozeMode)
        val flexInterval = calculateFlexInterval(syncInterval)
        
        Log.d(TAG, "Scheduling intelligent sync - battery: $batteryLevel%, charging: $isCharging, " +
                "doze: $isDozeMode, interval: ${syncInterval}min")
        
        val constraints = buildConstraints(batteryLevel, isCharging)
        
        val periodicSyncRequest = PeriodicWorkRequestBuilder<BackgroundSyncWorker>(
            syncInterval, TimeUnit.MINUTES,
            flexInterval, TimeUnit.MINUTES
        )
            .setConstraints(constraints)
            .setBackoffCriteria(
                BackoffPolicy.EXPONENTIAL,
                INITIAL_BACKOFF_SECONDS,
                TimeUnit.SECONDS
            )
            .setInputData(
                workDataOf(
                    BackgroundSyncWorker.KEY_SYNC_REASON to "intelligent_periodic",
                    BackgroundSyncWorker.KEY_PRIORITY to 1,
                    "battery_level" to batteryLevel,
                    "is_charging" to isCharging
                )
            )
            .addTag("intelligent_sync")
            .build()
        
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            "intelligent_periodic_sync",
            ExistingPeriodicWorkPolicy.REPLACE, // Replace to update with new battery-aware settings
            periodicSyncRequest
        )
    }
    
    /**
     * Schedule expedited sync for critical operations with Doze mode bypass
     */
    fun scheduleExpeditedSync(context: Context, reason: String = "critical_operation") {
        Log.d(TAG, "Scheduling expedited sync for critical operation: $reason")
        
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()
        
        val expeditedRequest = OneTimeWorkRequestBuilder<BackgroundSyncWorker>()
            .setConstraints(constraints)
            .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
            .setInputData(
                workDataOf(
                    BackgroundSyncWorker.KEY_SYNC_REASON to reason,
                    BackgroundSyncWorker.KEY_PRIORITY to 4, // Highest priority
                    "expedited" to true
                )
            )
            .addTag("expedited_sync")
            .build()
        
        WorkManager.getInstance(context).enqueue(expeditedRequest)
    }
    
    /**
     * Calculate optimal sync interval based on device state
     */
    private fun calculateOptimalSyncInterval(
        batteryLevel: Int,
        isCharging: Boolean,
        isDozeMode: Boolean
    ): Long {
        return when {
            isCharging -> {
                // More frequent sync when charging
                NORMAL_SYNC_INTERVAL_MINUTES
            }
            isDozeMode -> {
                // Longer intervals during Doze mode
                DOZE_MODE_SYNC_INTERVAL_MINUTES
            }
            batteryLevel <= VERY_LOW_BATTERY_THRESHOLD -> {
                // Very conservative sync when battery is critically low
                VERY_LOW_BATTERY_SYNC_INTERVAL_MINUTES
            }
            batteryLevel <= LOW_BATTERY_THRESHOLD -> {
                // Reduced sync frequency when battery is low
                LOW_BATTERY_SYNC_INTERVAL_MINUTES
            }
            else -> {
                // Normal sync interval
                NORMAL_SYNC_INTERVAL_MINUTES
            }
        }
    }
    
    /**
     * Calculate flex interval for WorkManager (allows system to optimize timing)
     */
    private fun calculateFlexInterval(syncInterval: Long): Long {
        return min(syncInterval / 3, 15L) // Up to 1/3 of interval, max 15 minutes
    }
    
    /**
     * Build constraints based on device state
     */
    private fun buildConstraints(batteryLevel: Int, isCharging: Boolean): Constraints {
        return Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .setRequiresBatteryNotLow(!isCharging && batteryLevel > LOW_BATTERY_THRESHOLD)
            .setRequiresCharging(false) // Allow sync even when not charging
            .setRequiresDeviceIdle(false) // Can sync when device is in use
            .setRequiresStorageNotLow(true) // Ensure sufficient storage
            .build()
    }
    
    /**
     * Get current battery level percentage
     */
    private fun getBatteryLevel(context: Context): Int {
        return try {
            val batteryManager = context.getSystemService(Context.BATTERY_SERVICE) as android.os.BatteryManager
            batteryManager.getIntProperty(android.os.BatteryManager.BATTERY_PROPERTY_CAPACITY)
        } catch (e: Exception) {
            Log.w(TAG, "Could not get battery level", e)
            100 // Assume full battery if we can't determine
        }
    }
    
    /**
     * Check if device is currently charging
     */
    private fun isDeviceCharging(context: Context): Boolean {
        return try {
            val batteryManager = context.getSystemService(Context.BATTERY_SERVICE) as android.os.BatteryManager
            batteryManager.isCharging
        } catch (e: Exception) {
            Log.w(TAG, "Could not determine charging state", e)
            false
        }
    }
    
    /**
     * Check if device is in Doze mode (Android 6+ power optimization)
     */
    private fun isDozeMode(context: Context): Boolean {
        return try {
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.M) {
                val powerManager = context.getSystemService(Context.POWER_SERVICE) as PowerManager
                powerManager.isDeviceIdleMode
            } else {
                false
            }
        } catch (e: Exception) {
            Log.w(TAG, "Could not determine Doze mode state", e)
            false
        }
    }
    
    /**
     * Calculate exponential backoff delay with jitter
     */
    fun calculateBackoffDelay(attemptCount: Int, baseDelaySeconds: Long = INITIAL_BACKOFF_SECONDS): Long {
        val exponentialDelay = (baseDelaySeconds * BACKOFF_MULTIPLIER.pow(attemptCount.toDouble())).toLong()
        val cappedDelay = min(exponentialDelay, MAX_BACKOFF_SECONDS)
        
        // Add jitter to prevent thundering herd
        val jitter = (Math.random() * 0.1 * cappedDelay).toLong()
        
        return cappedDelay + jitter
    }
    
    /**
     * Check if sync should be allowed based on current device state
     */
    fun shouldAllowSync(context: Context, priority: Int = 1): Boolean {
        val batteryLevel = getBatteryLevel(context)
        val isCharging = isDeviceCharging(context)
        val isDozeMode = isDozeMode(context)
        val networkUtils = NetworkUtils(context)
        
        return when {
            // Always allow high priority syncs (duty operations)
            priority >= 3 -> {
                networkUtils.isNetworkAvailable()
            }
            // Block sync if battery is very low and not charging
            batteryLevel <= VERY_LOW_BATTERY_THRESHOLD && !isCharging -> {
                Log.d(TAG, "Blocking sync - battery too low ($batteryLevel%) and not charging")
                false
            }
            // Allow sync during Doze mode only for medium+ priority
            isDozeMode && priority < 2 -> {
                Log.d(TAG, "Blocking low priority sync during Doze mode")
                false
            }
            // Check network availability
            !networkUtils.isNetworkAvailable() -> {
                Log.d(TAG, "Blocking sync - no network available")
                false
            }
            else -> true
        }
    }
    
    /**
     * Get sync statistics for monitoring
     */
    fun getSyncScheduleInfo(context: Context): SyncScheduleInfo {
        val batteryLevel = getBatteryLevel(context)
        val isCharging = isDeviceCharging(context)
        val isDozeMode = isDozeMode(context)
        val nextSyncInterval = calculateOptimalSyncInterval(batteryLevel, isCharging, isDozeMode)
        
        return SyncScheduleInfo(
            batteryLevel = batteryLevel,
            isCharging = isCharging,
            isDozeMode = isDozeMode,
            nextSyncIntervalMinutes = nextSyncInterval,
            batteryOptimizationActive = batteryLevel <= LOW_BATTERY_THRESHOLD && !isCharging
        )
    }
}

/**
 * Information about current sync scheduling state
 */
data class SyncScheduleInfo(
    val batteryLevel: Int,
    val isCharging: Boolean,
    val isDozeMode: Boolean,
    val nextSyncIntervalMinutes: Long,
    val batteryOptimizationActive: Boolean
)