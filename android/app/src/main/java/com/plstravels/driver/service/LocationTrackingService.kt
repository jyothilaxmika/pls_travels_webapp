package com.plstravels.driver.service

import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.location.Location
import android.os.Build
import android.os.IBinder
import android.os.Looper
import androidx.core.app.NotificationCompat
import com.google.android.gms.location.*
import com.plstravels.driver.data.local.LocationDao
import com.plstravels.driver.data.models.LocationPoint
import com.plstravels.driver.data.models.LocationSession
import com.plstravels.driver.data.models.LocationTrackingConfig
import com.plstravels.driver.data.repository.LocationRepository
import com.plstravels.driver.utils.LocationPermissionHelper
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.*
import javax.inject.Inject

/**
 * Foreground service for background location tracking during duty
 * Implements battery-optimized location tracking with offline storage
 */
@AndroidEntryPoint
class LocationTrackingService : Service() {
    
    @Inject
    lateinit var locationDao: LocationDao
    
    @Inject
    lateinit var locationRepository: LocationRepository
    
    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private lateinit var locationCallback: LocationCallback
    private lateinit var locationRequest: LocationRequest
    
    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val config = LocationTrackingConfig()
    
    private var currentDutyId: Int? = null
    private var currentSessionId: Long? = null
    private var isTracking = false
    private var lastLocation: Location? = null
    private var totalDistance = 0.0
    private var pointCount = 0
    
    companion object {
        private const val NOTIFICATION_ID = 1001
        private const val CHANNEL_ID = "location_tracking"
        const val ACTION_START_TRACKING = "START_TRACKING"
        const val ACTION_STOP_TRACKING = "STOP_TRACKING"
        const val EXTRA_DUTY_ID = "duty_id"
    }
    
    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        initializeLocationTracking()
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // Start foreground service immediately to comply with Android requirements
        startForeground(NOTIFICATION_ID, createNotification("Initializing location tracking..."))
        
        when (intent?.action) {
            ACTION_START_TRACKING -> {
                val dutyId = intent.getIntExtra(EXTRA_DUTY_ID, -1)
                if (dutyId != -1) {
                    startLocationTracking(dutyId)
                }
            }
            ACTION_STOP_TRACKING -> {
                stopLocationTracking()
            }
        }
        
        return START_STICKY
    }
    
    override fun onBind(intent: Intent?): IBinder? = null
    
    override fun onDestroy() {
        super.onDestroy()
        stopLocationTracking()
        serviceScope.cancel()
    }
    
    private fun initializeLocationTracking() {
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)
        
        // Create location request with battery optimization
        locationRequest = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, config.intervalMillis)
            .setMinUpdateIntervalMillis(config.fastestIntervalMillis)
            .setMinUpdateDistanceMeters(config.smallestDisplacementMeters)
            .setMaxUpdateDelayMillis(config.maxWaitTimeMillis)
            .setWaitForAccurateLocation(false)
            .build()
        
        // Location callback
        locationCallback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                super.onLocationResult(result)
                handleLocationUpdate(result)
            }
            
            override fun onLocationAvailability(availability: LocationAvailability) {
                super.onLocationAvailability(availability)
                // Handle location availability changes
                if (!availability.isLocationAvailable) {
                    updateNotification("Location unavailable")
                }
            }
        }
    }
    
    @SuppressLint("MissingPermission")
    private fun startLocationTracking(dutyId: Int) {
        if (isTracking) return
        
        // Check permissions
        if (!LocationPermissionHelper.hasLocationPermissions(this)) {
            stopSelf()
            return
        }
        
        currentDutyId = dutyId
        isTracking = true
        totalDistance = 0.0
        pointCount = 0
        
        // Start foreground service
        startForeground(NOTIFICATION_ID, createNotification("Starting location tracking..."))
        
        // Create location session
        serviceScope.launch {
            try {
                val session = LocationSession(
                    dutyId = dutyId,
                    startTime = System.currentTimeMillis(),
                    isActive = true
                )
                currentSessionId = locationDao.insertLocationSession(session)
                
                // Start location updates
                fusedLocationClient.requestLocationUpdates(
                    locationRequest,
                    locationCallback,
                    Looper.getMainLooper()
                )
                
                updateNotification("Tracking duty #$dutyId")
                
                // Schedule periodic sync
                schedulePeriodicSync()
                
            } catch (e: Exception) {
                // Handle error
                updateNotification("Error starting tracking")
                stopSelf()
            }
        }
    }
    
    private fun stopLocationTracking() {
        if (!isTracking) return
        
        isTracking = false
        
        // Stop location updates
        fusedLocationClient.removeLocationUpdates(locationCallback)
        
        // End location session
        serviceScope.launch {
            currentSessionId?.let { sessionId ->
                locationDao.endLocationSession(sessionId, System.currentTimeMillis())
                locationDao.updateLocationSessionStats(sessionId, totalDistance, pointCount)
            }
            
            // Final sync attempt
            locationRepository.syncPendingLocations()
        }
        
        // Stop foreground service
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }
    
    private fun handleLocationUpdate(locationResult: LocationResult) {
        if (!isTracking || currentDutyId == null) return
        
        serviceScope.launch {
            try {
                locationResult.locations.forEach { location ->
                    processLocationUpdate(location)
                }
            } catch (e: Exception) {
                // Handle processing error
            }
        }
    }
    
    private suspend fun processLocationUpdate(location: Location) {
        // Calculate distance from last location
        lastLocation?.let { last ->
            val distance = last.distanceTo(location).toDouble()
            totalDistance += distance
            
            // Update session stats periodically
            currentSessionId?.let { sessionId ->
                if (pointCount % 10 == 0) { // Update every 10 points
                    locationDao.updateLocationSessionStats(sessionId, totalDistance, pointCount + 1)
                }
            }
        }
        
        // Create location point
        val locationPoint = LocationPoint(
            latitude = location.latitude,
            longitude = location.longitude,
            accuracy = location.accuracy,
            altitude = if (location.hasAltitude()) location.altitude else null,
            bearing = if (location.hasBearing()) location.bearing else null,
            speed = if (location.hasSpeed()) location.speed else null,
            timestamp = location.time,
            dutyId = currentDutyId,
            isSynced = false
        )
        
        // Store location point
        locationDao.insertLocationPoint(locationPoint)
        pointCount++
        
        // Update notification with latest info
        updateNotification("Tracking: ${pointCount} points, ${String.format("%.1f", totalDistance/1000)} km")
        
        lastLocation = location
        
        // Trigger sync if we have enough points
        val unsyncedCount = locationDao.getUnsyncedCount()
        if (unsyncedCount >= config.batchSizeLimit) {
            locationRepository.syncPendingLocations()
        }
    }
    
    private fun schedulePeriodicSync() {
        serviceScope.launch {
            while (isTracking) {
                delay(config.syncIntervalMinutes * 60 * 1000) // Convert minutes to milliseconds
                if (isTracking) {
                    locationRepository.syncPendingLocations()
                }
            }
        }
    }
    
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Location Tracking",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Tracks driver location during active duty"
                setShowBadge(false)
            }
            
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }
    
    private fun createNotification(content: String) = NotificationCompat.Builder(this, CHANNEL_ID)
        .setContentTitle("PLS Travels - On Duty")
        .setContentText(content)
        .setSmallIcon(android.R.drawable.ic_menu_mylocation)
        .setOngoing(true)
        .setSilent(true)
        .setCategory(NotificationCompat.CATEGORY_SERVICE)
        .build()
    
    private fun updateNotification(content: String) {
        val notification = createNotification(content)
        val manager = getSystemService(NotificationManager::class.java)
        manager.notify(NOTIFICATION_ID, notification)
    }
}