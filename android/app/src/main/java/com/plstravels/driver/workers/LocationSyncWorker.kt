package com.plstravels.driver.workers

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.*
import com.plstravels.driver.data.repository.LocationRepository
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import java.util.concurrent.TimeUnit

/**
 * WorkManager worker for syncing location data in background
 * Runs periodically to upload cached location points when network is available
 */
@HiltWorker
class LocationSyncWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted workerParams: WorkerParameters,
    private val locationRepository: LocationRepository
) : CoroutineWorker(context, workerParams) {
    
    companion object {
        const val WORK_NAME = "location_sync_worker"
        private const val MAX_RETRY_ATTEMPTS = 3
        
        /**
         * Schedule periodic location sync work
         */
        fun schedulePeriodicSync(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .setRequiresBatteryNotLow(true)
                .build()
            
            val syncRequest = PeriodicWorkRequestBuilder<LocationSyncWorker>(
                15, TimeUnit.MINUTES, // Repeat every 15 minutes
                5, TimeUnit.MINUTES   // Flex interval
            )
                .setConstraints(constraints)
                .setBackoffCriteria(
                    BackoffPolicy.EXPONENTIAL,
                    WorkRequest.MIN_BACKOFF_MILLIS,
                    TimeUnit.MILLISECONDS
                )
                .build()
            
            WorkManager.getInstance(context)
                .enqueueUniquePeriodicWork(
                    WORK_NAME,
                    ExistingPeriodicWorkPolicy.KEEP,
                    syncRequest
                )
        }
        
        /**
         * Schedule one-time immediate sync
         */
        fun scheduleImmediateSync(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()
            
            val syncRequest = OneTimeWorkRequestBuilder<LocationSyncWorker>()
                .setConstraints(constraints)
                .setBackoffCriteria(
                    BackoffPolicy.EXPONENTIAL,
                    WorkRequest.MIN_BACKOFF_MILLIS,
                    TimeUnit.MILLISECONDS
                )
                .build()
            
            WorkManager.getInstance(context)
                .enqueueUniqueWork(
                    "immediate_location_sync",
                    ExistingWorkPolicy.REPLACE,
                    syncRequest
                )
        }
        
        /**
         * Cancel all location sync work
         */
        fun cancelAllWork(context: Context) {
            WorkManager.getInstance(context)
                .cancelUniqueWork(WORK_NAME)
        }
    }
    
    override suspend fun doWork(): Result {
        return try {
            // Check if there are any unsynced location points
            val unsyncedCount = locationRepository.getUnsyncedLocationCount()
            
            if (unsyncedCount == 0) {
                return Result.success()
            }
            
            // Attempt to sync pending locations using new batch endpoint
            val syncResult = locationRepository.syncPendingLocationsBatch()
            
            if (syncResult.isSuccess) {
                val syncedCount = syncResult.getOrNull() ?: 0
                
                // Create output data with sync results
                val outputData = workDataOf(
                    "synced_count" to syncedCount,
                    "timestamp" to System.currentTimeMillis()
                )
                
                Result.success(outputData)
            } else {
                // Check retry attempts
                if (runAttemptCount >= MAX_RETRY_ATTEMPTS) {
                    // Max retries reached, mark as success to avoid infinite retries
                    Result.success()
                } else {
                    // Retry with exponential backoff
                    Result.retry()
                }
            }
            
        } catch (e: Exception) {
            // Handle unexpected errors
            if (runAttemptCount >= MAX_RETRY_ATTEMPTS) {
                Result.failure()
            } else {
                Result.retry()
            }
        }
    }
}