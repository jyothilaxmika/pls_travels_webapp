package com.plstravels.driver.utils

import android.content.Context
import android.location.Location
import android.os.PowerManager
import androidx.work.*
import com.google.android.gms.location.*
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicLong
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Location tracking optimizer for battery-efficient location updates
 * Implements adaptive location tracking based on battery level, movement, and duty status
 */
@Singleton
class LocationTrackingOptimizer @Inject constructor(
    @ApplicationContext private val context: Context,
    private val logger: ProdLogger,
    private val memoryManager: MemoryManager
) : MemoryManager.MemoryListener {
    
    private val optimizationScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val powerManager = context.getSystemService(Context.POWER_SERVICE) as PowerManager
    
    // Tracking state
    private var currentOptimizationLevel = OptimizationLevel.BALANCED
    private var batteryOptimizedMode = false
    private var isMoving = false
    private var lastSignificantLocation: Location? = null
    
    // Metrics
    private val locationUpdateCount = AtomicLong(0)
    private val batteryOptimizedUpdateCount = AtomicLong(0)
    private val lastBatteryLevel = AtomicLong(100)
    
    // Location request configurations
    private val locationConfigs = mapOf(
        OptimizationLevel.POWER_SAVE to LocationConfig(
            intervalMs = 60_000L,        // 1 minute
            fastestIntervalMs = 30_000L,  // 30 seconds
            smallestDisplacementM = 20f,  // 20 meters
            priority = Priority.PRIORITY_BALANCED_POWER_ACCURACY
        ),
        OptimizationLevel.BALANCED to LocationConfig(
            intervalMs = 30_000L,        // 30 seconds
            fastestIntervalMs = 15_000L,  // 15 seconds
            smallestDisplacementM = 10f,  // 10 meters
            priority = Priority.PRIORITY_HIGH_ACCURACY
        ),
        OptimizationLevel.HIGH_ACCURACY to LocationConfig(
            intervalMs = 10_000L,        // 10 seconds
            fastestIntervalMs = 5_000L,   // 5 seconds
            smallestDisplacementM = 5f,   // 5 meters
            priority = Priority.PRIORITY_HIGH_ACCURACY
        )
    )
    
    companion object {
        private const val TAG = "LocationTrackingOptimizer"
        private const val LOW_BATTERY_THRESHOLD = 20
        private const val CRITICAL_BATTERY_THRESHOLD = 10
        private const val SIGNIFICANT_MOVEMENT_THRESHOLD = 50f // meters
        private const val STATIONARY_TIMEOUT_MS = 5 * 60 * 1000L // 5 minutes
        private const val GEOFENCE_RADIUS = 100f // meters
    }
    
    enum class OptimizationLevel {
        POWER_SAVE,      // Maximum battery savings
        BALANCED,        // Balance between accuracy and battery
        HIGH_ACCURACY    // Maximum accuracy for active tracking
    }
    
    data class LocationConfig(
        val intervalMs: Long,
        val fastestIntervalMs: Long,
        val smallestDisplacementM: Float,
        val priority: Int,
        val maxWaitTimeMs: Long = intervalMs * 3
    )
    
    data class LocationMetrics(
        val totalUpdates: Long,
        val batteryOptimizedUpdates: Long,
        val averageAccuracy: Float,
        val batteryLevel: Int,
        val optimizationLevel: OptimizationLevel,
        val isMoving: Boolean,
        val lastUpdateTime: Long
    )
    
    data class MovementState(
        val isMoving: Boolean,
        val speed: Float,
        val bearing: Float,
        val lastSignificantMovementTime: Long,
        val stationaryDuration: Long
    )
    
    fun initialize() {
        memoryManager.addMemoryListener(this)
        startBatteryMonitoring()
        startMovementDetection()
        logger.i(TAG, "Location tracking optimizer initialized")
    }
    
    private fun startBatteryMonitoring() {
        optimizationScope.launch {
            while (isActive) {
                try {
                    val batteryLevel = getBatteryLevel()
                    lastBatteryLevel.set(batteryLevel.toLong())
                    
                    val newOptimizationLevel = calculateOptimalLevel(batteryLevel)
                    if (newOptimizationLevel != currentOptimizationLevel) {
                        setOptimizationLevel(newOptimizationLevel)
                    }
                    
                    delay(60_000L) // Check every minute
                } catch (e: Exception) {
                    logger.e(TAG, "Error in battery monitoring", throwable = e)
                    delay(60_000L)
                }
            }
        }
    }
    
    private fun startMovementDetection() {
        optimizationScope.launch {
            while (isActive) {
                try {
                    detectMovementState()
                    delay(30_000L) // Check every 30 seconds
                } catch (e: Exception) {
                    logger.e(TAG, "Error in movement detection", throwable = e)
                    delay(30_000L)
                }
            }
        }
    }
    
    private fun calculateOptimalLevel(batteryLevel: Int): OptimizationLevel {
        return when {
            batteryLevel <= CRITICAL_BATTERY_THRESHOLD -> OptimizationLevel.POWER_SAVE
            batteryLevel <= LOW_BATTERY_THRESHOLD -> {
                if (isMoving) OptimizationLevel.BALANCED else OptimizationLevel.POWER_SAVE
            }
            powerManager.isPowerSaveMode -> OptimizationLevel.POWER_SAVE
            isMoving -> OptimizationLevel.HIGH_ACCURACY
            else -> OptimizationLevel.BALANCED
        }
    }
    
    private suspend fun detectMovementState() {
        // This would integrate with actual location updates
        // For now, it's a placeholder for movement detection logic
        val currentTime = System.currentTimeMillis()
        val lastLocation = lastSignificantLocation
        
        if (lastLocation != null) {
            val timeSinceLastUpdate = currentTime - lastLocation.time
            
            if (timeSinceLastUpdate > STATIONARY_TIMEOUT_MS) {
                if (isMoving) {
                    isMoving = false
                    logger.d(TAG, "Device detected as stationary")
                    optimizeForStationaryMode()
                }
            }
        }
    }
    
    private fun optimizeForStationaryMode() {
        optimizationScope.launch {
            // Switch to geofencing when stationary
            setupGeofencing()
            
            // Reduce location update frequency
            if (currentOptimizationLevel == OptimizationLevel.HIGH_ACCURACY) {
                setOptimizationLevel(OptimizationLevel.BALANCED)
            }
        }
    }
    
    private suspend fun setupGeofencing() {
        withContext(Dispatchers.IO) {
            try {
                val lastLocation = lastSignificantLocation ?: return@withContext
                
                // Create geofence around current location
                val geofence = Geofence.Builder()
                    .setRequestId("stationary_geofence")
                    .setCircularRegion(
                        lastLocation.latitude,
                        lastLocation.longitude,
                        GEOFENCE_RADIUS
                    )
                    .setExpirationDuration(Geofence.NEVER_EXPIRE)
                    .setTransitionTypes(Geofence.GEOFENCE_TRANSITION_EXIT)
                    .build()
                
                logger.d(TAG, "Geofence setup for stationary detection")
                
            } catch (e: Exception) {
                logger.e(TAG, "Error setting up geofencing", throwable = e)
            }
        }
    }
    
    /**
     * Get optimized location request based on current state
     */
    fun getOptimizedLocationRequest(): LocationRequest {
        val config = locationConfigs[currentOptimizationLevel] 
            ?: locationConfigs[OptimizationLevel.BALANCED]!!
        
        return LocationRequest.Builder(config.priority, config.intervalMs)
            .setMinUpdateIntervalMillis(config.fastestIntervalMs)
            .setMinUpdateDistanceMeters(config.smallestDisplacementM)
            .setMaxUpdateDelayMillis(config.maxWaitTimeMs)
            .setWaitForAccurateLocation(currentOptimizationLevel == OptimizationLevel.HIGH_ACCURACY)
            .build()
    }
    
    /**
     * Process location update with optimization logic
     */
    fun processLocationUpdate(location: Location): Boolean {
        locationUpdateCount.incrementAndGet()
        
        val shouldProcess = shouldProcessLocation(location)
        
        if (shouldProcess) {
            updateMovementState(location)
            lastSignificantLocation = location
            
            if (batteryOptimizedMode) {
                batteryOptimizedUpdateCount.incrementAndGet()
            }
        }
        
        return shouldProcess
    }
    
    private fun shouldProcessLocation(location: Location): Boolean {
        val lastLocation = lastSignificantLocation ?: return true
        
        // Check accuracy threshold
        if (location.accuracy > getAccuracyThreshold()) {
            logger.d(TAG, "Location rejected due to poor accuracy: ${location.accuracy}m")
            return false
        }
        
        // Check distance threshold
        val distance = lastLocation.distanceTo(location)
        val minDistance = locationConfigs[currentOptimizationLevel]?.smallestDisplacementM ?: 10f
        
        if (distance < minDistance) {
            logger.d(TAG, "Location rejected due to insufficient movement: ${distance}m")
            return false
        }
        
        // Check time threshold for battery optimization
        if (batteryOptimizedMode) {
            val timeSinceLastUpdate = System.currentTimeMillis() - lastLocation.time
            val minInterval = locationConfigs[currentOptimizationLevel]?.intervalMs ?: 30_000L
            
            if (timeSinceLastUpdate < minInterval) {
                return false
            }
        }
        
        return true
    }
    
    private fun updateMovementState(location: Location) {
        val lastLocation = lastSignificantLocation
        
        if (lastLocation != null) {
            val distance = lastLocation.distanceTo(location)
            val timeDiff = (location.time - lastLocation.time) / 1000f // seconds
            
            if (distance > SIGNIFICANT_MOVEMENT_THRESHOLD && timeDiff > 0) {
                if (!isMoving) {
                    isMoving = true
                    logger.d(TAG, "Movement detected - optimizing for active tracking")
                    
                    // Adjust optimization level for movement
                    if (currentOptimizationLevel == OptimizationLevel.POWER_SAVE) {
                        setOptimizationLevel(OptimizationLevel.BALANCED)
                    }
                }
            }
        }
    }
    
    private fun getAccuracyThreshold(): Float {
        return when (currentOptimizationLevel) {
            OptimizationLevel.POWER_SAVE -> 50f      // 50 meters
            OptimizationLevel.BALANCED -> 25f        // 25 meters  
            OptimizationLevel.HIGH_ACCURACY -> 15f   // 15 meters
        }
    }
    
    /**
     * Set optimization level and update location request
     */
    fun setOptimizationLevel(level: OptimizationLevel) {
        val previousLevel = currentOptimizationLevel
        currentOptimizationLevel = level
        
        // Update battery optimized mode
        batteryOptimizedMode = level == OptimizationLevel.POWER_SAVE
        
        logger.i(TAG, "Location optimization level changed", mapOf(
            "from" to previousLevel.name,
            "to" to level.name,
            "battery_level" to lastBatteryLevel.get().toString(),
            "is_moving" to isMoving.toString()
        ))
    }
    
    /**
     * Create WorkManager request for background location updates
     */
    fun createBackgroundLocationWork(): WorkRequest {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .setRequiresBatteryNotLow(currentOptimizationLevel != OptimizationLevel.POWER_SAVE)
            .build()
        
        val interval = when (currentOptimizationLevel) {
            OptimizationLevel.POWER_SAVE -> 15L      // 15 minutes
            OptimizationLevel.BALANCED -> 10L        // 10 minutes
            OptimizationLevel.HIGH_ACCURACY -> 5L    // 5 minutes
        }
        
        return PeriodicWorkRequestBuilder<LocationSyncWorker>(interval, TimeUnit.MINUTES)
            .setConstraints(constraints)
            .setBackoffCriteria(
                BackoffPolicy.EXPONENTIAL,
                WorkRequest.MIN_BACKOFF_MILLIS,
                TimeUnit.MILLISECONDS
            )
            .addTag("optimized_location_sync")
            .build()
    }
    
    /**
     * Get current tracking metrics
     */
    fun getTrackingMetrics(): LocationMetrics {
        return LocationMetrics(
            totalUpdates = locationUpdateCount.get(),
            batteryOptimizedUpdates = batteryOptimizedUpdateCount.get(),
            averageAccuracy = calculateAverageAccuracy(),
            batteryLevel = lastBatteryLevel.get().toInt(),
            optimizationLevel = currentOptimizationLevel,
            isMoving = isMoving,
            lastUpdateTime = lastSignificantLocation?.time ?: 0L
        )
    }
    
    private fun calculateAverageAccuracy(): Float {
        // This would be calculated from stored location history
        // For now, return a placeholder value
        return when (currentOptimizationLevel) {
            OptimizationLevel.POWER_SAVE -> 30f
            OptimizationLevel.BALANCED -> 20f
            OptimizationLevel.HIGH_ACCURACY -> 10f
        }
    }
    
    /**
     * Get movement state information
     */
    fun getMovementState(): MovementState {
        val lastLocation = lastSignificantLocation
        
        return MovementState(
            isMoving = isMoving,
            speed = lastLocation?.speed ?: 0f,
            bearing = lastLocation?.bearing ?: 0f,
            lastSignificantMovementTime = lastLocation?.time ?: 0L,
            stationaryDuration = if (!isMoving && lastLocation != null) {
                System.currentTimeMillis() - lastLocation.time
            } else 0L
        )
    }
    
    /**
     * Force optimization level (for testing or manual override)
     */
    fun forceOptimizationLevel(level: OptimizationLevel, reason: String) {
        logger.i(TAG, "Force optimization level change: $reason", mapOf(
            "new_level" to level.name
        ))
        setOptimizationLevel(level)
    }
    
    private fun getBatteryLevel(): Int {
        return try {
            val batteryManager = context.getSystemService(Context.BATTERY_SERVICE) as android.os.BatteryManager
            batteryManager.getIntProperty(android.os.BatteryManager.BATTERY_PROPERTY_CAPACITY)
        } catch (e: Exception) {
            logger.e(TAG, "Error getting battery level", throwable = e)
            100 // Assume full battery on error
        }
    }
    
    // MemoryManager.MemoryListener implementation
    override fun onMemoryWarning(level: MemoryManager.MemoryLevel) {
        when (level) {
            MemoryManager.MemoryLevel.CRITICAL -> {
                forceOptimizationLevel(OptimizationLevel.POWER_SAVE, "Critical memory warning")
            }
            MemoryManager.MemoryLevel.LOW -> {
                if (currentOptimizationLevel == OptimizationLevel.HIGH_ACCURACY) {
                    setOptimizationLevel(OptimizationLevel.BALANCED)
                }
            }
            else -> {
                // No immediate action for normal memory levels
            }
        }
    }
    
    override fun onMemoryOptimizationRecommended() {
        // Reduce location update frequency temporarily
        optimizationScope.launch {
            delay(30_000L) // Reduce for 30 seconds
            // Resume normal operation
        }
    }
    
    fun shutdown() {
        logger.i(TAG, "Location tracking optimizer shutting down")
        optimizationScope.cancel()
        memoryManager.removeMemoryListener(this)
    }
}