package com.plstravels.driver.service

import android.content.Context
import android.util.Log
import com.plstravels.driver.data.repository.ConnectivityRepository
import com.plstravels.driver.utils.NetworkUtils
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.first
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Network-aware sync service that optimizes sync behavior based on connection type
 * Implements intelligent sync strategies for different network conditions
 */
@Singleton
class NetworkAwareSyncService @Inject constructor(
    private val connectivityRepository: ConnectivityRepository,
    private val backgroundSyncScheduler: BatteryOptimizedSyncScheduler,
    private val networkUtils: NetworkUtils
) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var isMonitoring = false
    
    companion object {
        private const val TAG = "NetworkAwareSyncService"
        
        // Sync priorities based on network type
        private const val WIFI_SYNC_PRIORITY = 3
        private const val CELLULAR_SYNC_PRIORITY = 2
        private const val METERED_SYNC_PRIORITY = 1
        
        // Data usage thresholds for metered connections
        private const val LIGHT_SYNC_DATA_THRESHOLD_MB = 5
        private const val FULL_SYNC_DATA_THRESHOLD_MB = 20
    }
    
    /**
     * Start monitoring network changes and adapting sync behavior
     */
    fun startNetworkAwareSync(context: Context) {
        if (isMonitoring) {
            Log.d(TAG, "Network monitoring already active")
            return
        }
        
        Log.d(TAG, "Starting network-aware sync monitoring")
        isMonitoring = true
        
        scope.launch {
            connectivityRepository.isConnected
                .distinctUntilChanged()
                .collect { isConnected ->
                    if (isConnected) {
                        handleNetworkConnected(context)
                    } else {
                        handleNetworkDisconnected(context)
                    }
                }
        }
        
        // Monitor network type changes
        scope.launch {
            connectivityRepository.getCurrentNetworkType()
            // Note: This would need flow support in ConnectivityRepository for real-time monitoring
            while (isActive && isMonitoring) {
                try {
                    val currentNetworkType = connectivityRepository.getCurrentNetworkType()
                    adaptSyncToNetworkType(context, currentNetworkType)
                    delay(60_000) // Check every minute
                } catch (e: Exception) {
                    Log.e(TAG, "Error monitoring network type", e)
                    delay(60_000)
                }
            }
        }
    }
    
    /**
     * Stop network monitoring
     */
    fun stopNetworkAwareSync() {
        Log.d(TAG, "Stopping network-aware sync monitoring")
        isMonitoring = false
        scope.cancel()
    }
    
    /**
     * Handle network connection established
     */
    private fun handleNetworkConnected(context: Context) {
        Log.d(TAG, "Network connected - triggering immediate sync")
        
        val networkType = connectivityRepository.getCurrentNetworkType()
        val isMetered = connectivityRepository.isMeteredConnection()
        
        when {
            networkType == ConnectivityRepository.NetworkType.WIFI -> {
                // WiFi connection - schedule immediate high-priority sync
                BackgroundSyncScheduler.scheduleImmediateSync(
                    context, 
                    BackgroundSyncWorker.REASON_CONNECTIVITY_RESTORED
                )
            }
            isMetered -> {
                // Metered connection - schedule limited sync
                scheduleMeteredSync(context)
            }
            else -> {
                // Non-metered cellular - schedule normal sync
                BackgroundSyncScheduler.scheduleImmediateSync(
                    context,
                    BackgroundSyncWorker.REASON_CONNECTIVITY_RESTORED
                )
            }
        }
        
        // Update periodic sync schedule based on new network type
        adaptSyncToNetworkType(context, networkType)
    }
    
    /**
     * Handle network disconnection
     */
    private fun handleNetworkDisconnected(context: Context) {
        Log.d(TAG, "Network disconnected - canceling non-essential sync work")
        
        // Cancel non-essential background sync work to save battery
        // Keep high-priority work that will retry when connection returns
        BackgroundSyncScheduler.cancelAllSync(context)
        
        // Reschedule only essential periodic work
        BatteryOptimizedSyncScheduler.scheduleIntelligentPeriodicSync(context)
    }
    
    /**
     * Adapt sync behavior to current network type
     */
    private fun adaptSyncToNetworkType(context: Context, networkType: ConnectivityRepository.NetworkType) {
        Log.d(TAG, "Adapting sync to network type: $networkType")
        
        when (networkType) {
            ConnectivityRepository.NetworkType.WIFI -> {
                // WiFi - enable full sync capabilities
                BatteryOptimizedSyncScheduler.scheduleIntelligentPeriodicSync(context)
            }
            ConnectivityRepository.NetworkType.CELLULAR -> {
                // Cellular - check if metered
                if (connectivityRepository.isMeteredConnection()) {
                    scheduleBandwidthAwareSync(context)
                } else {
                    BatteryOptimizedSyncScheduler.scheduleIntelligentPeriodicSync(context)
                }
            }
            ConnectivityRepository.NetworkType.NONE -> {
                // No connection - cancel sync work
                BackgroundSyncScheduler.cancelAllSync(context)
            }
        }
    }
    
    /**
     * Schedule sync optimized for metered connections
     */
    private fun scheduleMeteredSync(context: Context) {
        Log.d(TAG, "Scheduling metered connection sync")
        
        // Schedule immediate light sync for critical data only
        BackgroundSyncScheduler.scheduleImmediateSync(
            context,
            "metered_critical_sync"
        )
        
        // Schedule less frequent periodic sync to conserve data
        scheduleBandwidthAwareSync(context)
    }
    
    /**
     * Schedule bandwidth-aware sync for data conservation
     */
    private fun scheduleBandwidthAwareSync(context: Context) {
        Log.d(TAG, "Scheduling bandwidth-aware sync")
        
        // Use longer intervals and stricter constraints for metered connections
        val constraints = androidx.work.Constraints.Builder()
            .setRequiredNetworkType(androidx.work.NetworkType.CONNECTED)
            .setRequiresBatteryNotLow(true)
            .setRequiresStorageNotLow(true)
            .build()
        
        val bandwidthAwareRequest = androidx.work.PeriodicWorkRequestBuilder<BackgroundSyncWorker>(
            45, java.util.concurrent.TimeUnit.MINUTES, // Longer interval for metered
            15, java.util.concurrent.TimeUnit.MINUTES
        )
            .setConstraints(constraints)
            .setInputData(
                androidx.work.workDataOf(
                    BackgroundSyncWorker.KEY_SYNC_REASON to "bandwidth_aware",
                    BackgroundSyncWorker.KEY_PRIORITY to METERED_SYNC_PRIORITY,
                    "bandwidth_limit" to LIGHT_SYNC_DATA_THRESHOLD_MB
                )
            )
            .addTag("bandwidth_aware_sync")
            .build()
        
        androidx.work.WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            "bandwidth_aware_sync",
            androidx.work.ExistingPeriodicWorkPolicy.REPLACE,
            bandwidthAwareRequest
        )
    }
    
    /**
     * Determine sync priority based on current network conditions
     */
    fun getSyncPriority(): Int {
        val networkType = connectivityRepository.getCurrentNetworkType()
        val isMetered = connectivityRepository.isMeteredConnection()
        
        return when {
            networkType == ConnectivityRepository.NetworkType.WIFI -> WIFI_SYNC_PRIORITY
            networkType == ConnectivityRepository.NetworkType.CELLULAR && !isMetered -> CELLULAR_SYNC_PRIORITY
            isMetered -> METERED_SYNC_PRIORITY
            else -> 1 // Minimum priority
        }
    }
    
    /**
     * Check if full sync is recommended based on network conditions
     */
    suspend fun isFullSyncRecommended(): Boolean {
        val isConnected = connectivityRepository.isConnected.first()
        val networkType = connectivityRepository.getCurrentNetworkType()
        val isMetered = connectivityRepository.isMeteredConnection()
        
        return when {
            !isConnected -> false
            networkType == ConnectivityRepository.NetworkType.WIFI -> true
            networkType == ConnectivityRepository.NetworkType.CELLULAR && !isMetered -> true
            isMetered -> false // Only critical data on metered connections
            else -> false
        }
    }
    
    /**
     * Get network-aware sync recommendations
     */
    suspend fun getSyncRecommendations(): NetworkSyncRecommendations {
        val isConnected = connectivityRepository.isConnected.first()
        val networkType = connectivityRepository.getCurrentNetworkType()
        val isMetered = connectivityRepository.isMeteredConnection()
        val hasInternetConnection = connectivityRepository.hasInternetConnection()
        
        return NetworkSyncRecommendations(
            allowSync = isConnected && hasInternetConnection,
            recommendFullSync = isFullSyncRecommended(),
            syncPriority = getSyncPriority(),
            networkType = networkType.name,
            isMetered = isMetered,
            recommendedSyncIntervalMinutes = when {
                networkType == ConnectivityRepository.NetworkType.WIFI -> 15L
                isMetered -> 45L
                else -> 30L
            }
        )
    }
}

/**
 * Network-aware sync recommendations
 */
data class NetworkSyncRecommendations(
    val allowSync: Boolean,
    val recommendFullSync: Boolean,
    val syncPriority: Int,
    val networkType: String,
    val isMetered: Boolean,
    val recommendedSyncIntervalMinutes: Long
)