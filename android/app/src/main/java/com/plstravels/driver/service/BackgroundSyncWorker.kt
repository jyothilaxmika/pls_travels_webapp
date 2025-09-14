package com.plstravels.driver.service

import android.content.Context
import android.util.Log
import androidx.hilt.work.HiltWorker
import androidx.work.*
import com.plstravels.driver.data.repository.CommandQueueRepository
import com.plstravels.driver.utils.NetworkUtils
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import kotlinx.coroutines.delay
import java.util.concurrent.TimeUnit

/**
 * Background worker for periodic data synchronization
 * Uses WorkManager for battery-optimized background processing
 */
@HiltWorker
class BackgroundSyncWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted workerParams: WorkerParameters,
    private val commandQueueRepository: CommandQueueRepository,
    private val syncManager: SyncManager,
    private val networkUtils: NetworkUtils
) : CoroutineWorker(context, workerParams) {

    companion object {
        private const val TAG = "BackgroundSyncWorker"
        private const val WORK_NAME = "background_sync"
        private const val SYNC_INTERVAL_MINUTES = 15L
        private const val FLEX_INTERVAL_MINUTES = 5L
        private const val MAX_RETRY_ATTEMPTS = 3
        private const val INITIAL_BACKOFF_SECONDS = 30L
        
        // Input data keys
        const val KEY_SYNC_REASON = "sync_reason"
        const val KEY_PRIORITY = "priority"
        
        // Sync reasons
        const val REASON_PERIODIC = "periodic"
        const val REASON_CONNECTIVITY_RESTORED = "connectivity_restored"
        const val REASON_MANUAL = "manual"
        const val REASON_DUTY_OPERATION = "duty_operation"
    }

    override suspend fun doWork(): Result {
        val syncReason = inputData.getString(KEY_SYNC_REASON) ?: REASON_PERIODIC
        val priority = inputData.getInt(KEY_PRIORITY, 0)
        
        Log.d(TAG, "Starting background sync - reason: $syncReason, priority: $priority")
        
        return try {
            // Check if network is available
            if (!networkUtils.isNetworkAvailable()) {
                Log.d(TAG, "No network available - skipping sync")
                return Result.success()
            }
            
            // Check if we have pending commands to sync
            val pendingCommands = commandQueueRepository.getPendingCommandCount()
            if (pendingCommands == 0) {
                Log.d(TAG, "No pending commands - sync completed")
                return Result.success()
            }
            
            Log.d(TAG, "Found $pendingCommands pending commands - starting sync")
            
            // Perform synchronization with timeout
            val syncResult = performSyncWithTimeout()
            
            when (syncResult) {
                BackgroundSyncResult.SUCCESS -> {
                    Log.d(TAG, "Background sync completed successfully")
                    scheduleNextPeriodicSync()
                    Result.success()
                }
                BackgroundSyncResult.PARTIAL_SUCCESS -> {
                    Log.w(TAG, "Background sync partially successful - will retry")
                    Result.retry()
                }
                BackgroundSyncResult.FAILURE -> {
                    Log.e(TAG, "Background sync failed")
                    Result.failure()
                }
                BackgroundSyncResult.NETWORK_ERROR -> {
                    Log.w(TAG, "Network error during sync - will retry when network improves")
                    Result.retry()
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Exception during background sync", e)
            Result.failure()
        }
    }
    
    /**
     * Perform sync with timeout to prevent long-running background tasks
     */
    private suspend fun performSyncWithTimeout(): BackgroundSyncResult {
        return try {
            // Use withTimeout to prevent long-running sync operations
            kotlinx.coroutines.withTimeout(60_000L) { // 1 minute timeout
                syncManager.performFullSync()
            }
        } catch (e: kotlinx.coroutines.TimeoutCancellationException) {
            Log.w(TAG, "Sync timeout - operation took too long")
            BackgroundSyncResult.PARTIAL_SUCCESS
        } catch (e: Exception) {
            Log.e(TAG, "Sync error", e)
            if (networkUtils.isNetworkAvailable()) {
                BackgroundSyncResult.FAILURE
            } else {
                BackgroundSyncResult.NETWORK_ERROR
            }
        }
    }
    
    /**
     * Schedule the next periodic sync
     */
    private fun scheduleNextPeriodicSync() {
        BackgroundSyncScheduler.schedulePeriodicSync(applicationContext)
    }
    
}

/**
 * Scheduler for background sync operations
 */
object BackgroundSyncScheduler {
    private const val TAG = "BackgroundSyncScheduler"
    
    /**
     * Schedule periodic background sync with battery optimizations
     */
    fun schedulePeriodicSync(context: Context) {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .setRequiresBatteryNotLow(true) // Only sync when battery is not low
            .setRequiresDeviceIdle(false) // Can sync even when device is in use
            .build()
        
        val periodicSyncRequest = PeriodicWorkRequestBuilder<BackgroundSyncWorker>(
            BackgroundSyncWorker.SYNC_INTERVAL_MINUTES, TimeUnit.MINUTES,
            BackgroundSyncWorker.FLEX_INTERVAL_MINUTES, TimeUnit.MINUTES
        )
            .setConstraints(constraints)
            .setBackoffCriteria(
                BackoffPolicy.EXPONENTIAL,
                BackgroundSyncWorker.INITIAL_BACKOFF_SECONDS,
                TimeUnit.SECONDS
            )
            .setInputData(
                workDataOf(
                    BackgroundSyncWorker.KEY_SYNC_REASON to BackgroundSyncWorker.REASON_PERIODIC,
                    BackgroundSyncWorker.KEY_PRIORITY to 1
                )
            )
            .addTag("periodic_sync")
            .build()
        
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            BackgroundSyncWorker.WORK_NAME,
            ExistingPeriodicWorkPolicy.KEEP, // Keep existing work if already scheduled
            periodicSyncRequest
        )
        
        Log.d(TAG, "Scheduled periodic background sync every ${BackgroundSyncWorker.SYNC_INTERVAL_MINUTES} minutes")
    }
    
    /**
     * Schedule immediate sync when connectivity is restored
     */
    fun scheduleImmediateSync(context: Context, reason: String = BackgroundSyncWorker.REASON_MANUAL) {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()
        
        val immediateSyncRequest = OneTimeWorkRequestBuilder<BackgroundSyncWorker>()
            .setConstraints(constraints)
            .setInputData(
                workDataOf(
                    BackgroundSyncWorker.KEY_SYNC_REASON to reason,
                    BackgroundSyncWorker.KEY_PRIORITY to 2
                )
            )
            .addTag("immediate_sync")
            .build()
        
        WorkManager.getInstance(context).enqueue(immediateSyncRequest)
        
        Log.d(TAG, "Scheduled immediate background sync - reason: $reason")
    }
    
    /**
     * Schedule high-priority sync for critical operations
     */
    fun scheduleHighPrioritySync(context: Context, reason: String = BackgroundSyncWorker.REASON_DUTY_OPERATION) {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .setRequiresBatteryNotLow(false) // Allow even when battery is low for critical ops
            .build()
        
        val highPrioritySyncRequest = OneTimeWorkRequestBuilder<BackgroundSyncWorker>()
            .setConstraints(constraints)
            .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST) // Expedited for critical operations
            .setInputData(
                workDataOf(
                    BackgroundSyncWorker.KEY_SYNC_REASON to reason,
                    BackgroundSyncWorker.KEY_PRIORITY to 3
                )
            )
            .addTag("high_priority_sync")
            .build()
        
        WorkManager.getInstance(context).enqueue(highPrioritySyncRequest)
        
        Log.d(TAG, "Scheduled high-priority background sync - reason: $reason")
    }
    
    /**
     * Cancel all background sync work
     */
    fun cancelAllSync(context: Context) {
        WorkManager.getInstance(context).cancelUniqueWork(BackgroundSyncWorker.WORK_NAME)
        WorkManager.getInstance(context).cancelAllWorkByTag("immediate_sync")
        WorkManager.getInstance(context).cancelAllWorkByTag("high_priority_sync")
        
        Log.d(TAG, "Cancelled all background sync work")
    }
    
    /**
     * Get background sync work status
     */
    fun getSyncWorkStatus(context: Context): androidx.lifecycle.LiveData<List<WorkInfo>> {
        return WorkManager.getInstance(context).getWorkInfosByTagLiveData("periodic_sync")
    }
}