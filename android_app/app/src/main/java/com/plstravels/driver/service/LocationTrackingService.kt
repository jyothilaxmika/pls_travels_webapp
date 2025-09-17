package com.plstravels.driver.service

import android.annotation.SuppressLint
import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.location.Location
import android.os.IBinder
import android.os.Looper
import androidx.core.app.NotificationCompat
import com.google.android.gms.location.*
import com.plstravels.driver.PLSTravelsApplication
import com.plstravels.driver.R
import com.plstravels.driver.data.repository.LocationRepository
import com.plstravels.driver.ui.MainActivity
import com.plstravels.driver.utils.LocationPermissionHelper
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.*
import timber.log.Timber
import javax.inject.Inject

/**
 * Foreground service for location tracking during duty
 */
@AndroidEntryPoint
class LocationTrackingService : Service() {
    
    @Inject
    lateinit var locationRepository: LocationRepository
    
    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private lateinit var locationRequest: LocationRequest
    private lateinit var locationCallback: LocationCallback
    private lateinit var locationPermissionHelper: LocationPermissionHelper
    
    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var isTrackingActive = false
    private var lastLocationTime = 0L
    private var locationCount = 0
    
    companion object {
        const val ACTION_START_TRACKING = "START_TRACKING"
        const val ACTION_STOP_TRACKING = "STOP_TRACKING"
        
        // Location update intervals
        private const val LOCATION_UPDATE_INTERVAL = 30_000L // 30 seconds
        private const val LOCATION_UPDATE_FASTEST_INTERVAL = 15_000L // 15 seconds
        private const val LOCATION_UPDATE_MAX_WAIT_TIME = 60_000L // 1 minute
        
        // Sync intervals
        private const val SYNC_INTERVAL = 5 * 60_000L // 5 minutes
        
        fun startLocationTracking(context: Context) {
            val intent = Intent(context, LocationTrackingService::class.java).apply {
                action = ACTION_START_TRACKING
            }
            context.startForegroundService(intent)
        }
        
        fun stopLocationTracking(context: Context) {
            val intent = Intent(context, LocationTrackingService::class.java).apply {
                action = ACTION_STOP_TRACKING
            }
            context.startService(intent)
        }
    }
    
    override fun onBind(intent: Intent?): IBinder? = null
    
    override fun onCreate() {
        super.onCreate()
        
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)
        locationPermissionHelper = LocationPermissionHelper(this)
        
        setupLocationRequest()
        setupLocationCallback()
        
        Timber.d("LocationTrackingService created")
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START_TRACKING -> startLocationTracking()
            ACTION_STOP_TRACKING -> stopLocationTracking()
        }
        return START_STICKY // Restart service if killed
    }
    
    override fun onDestroy() {
        super.onDestroy()
        stopLocationUpdates()
        serviceScope.cancel()
        Timber.d("LocationTrackingService destroyed")
    }
    
    private fun setupLocationRequest() {
        locationRequest = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, LOCATION_UPDATE_INTERVAL)
            .setWaitForAccurateLocation(false)
            .setMinUpdateIntervalMillis(LOCATION_UPDATE_FASTEST_INTERVAL)
            .setMaxUpdateDelayMillis(LOCATION_UPDATE_MAX_WAIT_TIME)
            .build()
    }
    
    private fun setupLocationCallback() {
        locationCallback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                super.onLocationResult(result)
                
                result.lastLocation?.let { location ->
                    handleLocationUpdate(location)
                }
            }
            
            override fun onLocationAvailability(availability: LocationAvailability) {
                super.onLocationAvailability(availability)
                
                if (availability.isLocationAvailable) {
                    Timber.d("Location availability: Available")
                    updateNotification("Location tracking active", "GPS signal acquired")
                } else {
                    Timber.w("Location availability: Unavailable")
                    updateNotification("Location tracking active", "Searching for GPS signal...")
                }
            }
        }
    }
    
    private fun startLocationTracking() {
        if (isTrackingActive) {
            Timber.d("Location tracking already active")
            return
        }
        
        if (!locationPermissionHelper.hasLocationPermissions()) {
            Timber.w("Location permissions not granted")
            stopSelf()
            return
        }
        
        Timber.i("Starting location tracking")
        
        val notification = createNotification("Starting location tracking...")
        startForeground(PLSTravelsApplication.LOCATION_SERVICE_NOTIFICATION_ID, notification)
        
        startLocationUpdates()
        startPeriodicSync()
        
        isTrackingActive = true
    }
    
    private fun stopLocationTracking() {
        if (!isTrackingActive) {
            Timber.d("Location tracking already stopped")
            return
        }
        
        Timber.i("Stopping location tracking")
        
        stopLocationUpdates()
        isTrackingActive = false
        
        // Final sync before stopping
        serviceScope.launch {
            try {
                locationRepository.syncUnsyncedLocations()
                locationRepository.cleanupOldLocations()
            } catch (e: Exception) {
                Timber.e(e, "Error during final sync")
            }
        }
        
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }
    
    @SuppressLint("MissingPermission")
    private fun startLocationUpdates() {
        if (!locationPermissionHelper.hasLocationPermissions()) {
            Timber.e("Cannot start location updates: permissions not granted")
            return
        }
        
        try {
            fusedLocationClient.requestLocationUpdates(
                locationRequest,
                locationCallback,
                Looper.getMainLooper()
            )
            
            Timber.i("Location updates started")
            
            // Get last known location as initial point
            fusedLocationClient.lastLocation.addOnSuccessListener { location ->
                location?.let { handleLocationUpdate(it) }
            }
            
        } catch (e: SecurityException) {
            Timber.e(e, "Security exception when starting location updates")
            stopSelf()
        } catch (e: Exception) {
            Timber.e(e, "Error starting location updates")
            stopSelf()
        }
    }
    
    private fun stopLocationUpdates() {
        try {
            fusedLocationClient.removeLocationUpdates(locationCallback)
            Timber.i("Location updates stopped")
        } catch (e: Exception) {
            Timber.e(e, "Error stopping location updates")
        }
    }
    
    private fun handleLocationUpdate(location: Location) {
        try {
            val currentTime = System.currentTimeMillis()
            
            // Avoid duplicate locations (within 10 seconds and 10 meters)
            if (shouldFilterLocation(location, currentTime)) {
                return
            }
            
            lastLocationTime = currentTime
            locationCount++
            
            // Save location to database
            serviceScope.launch {
                try {
                    val result = locationRepository.saveLocation(
                        latitude = location.latitude,
                        longitude = location.longitude,
                        accuracy = location.accuracy,
                        speed = if (location.hasSpeed()) location.speed else 0f,
                        heading = if (location.hasBearing()) location.bearing else 0f
                    )
                    
                    result.fold(
                        onSuccess = {
                            Timber.d("Location saved: ${location.latitude}, ${location.longitude}")
                            updateNotification(
                                "Location tracking active",
                                "Locations recorded: $locationCount"
                            )
                        },
                        onFailure = { exception ->
                            Timber.e(exception, "Failed to save location")
                        }
                    )
                    
                } catch (e: Exception) {
                    Timber.e(e, "Error handling location update")
                }
            }
            
        } catch (e: Exception) {
            Timber.e(e, "Error in handleLocationUpdate")
        }
    }
    
    private fun shouldFilterLocation(location: Location, currentTime: Long): Boolean {
        // Filter out obviously bad locations
        if (location.accuracy > 100f) { // More than 100m accuracy
            Timber.d("Filtering location with poor accuracy: ${location.accuracy}m")
            return true
        }
        
        // Filter locations too close in time (less than 10 seconds)
        if (currentTime - lastLocationTime < 10_000) {
            Timber.d("Filtering location too close in time")
            return true
        }
        
        return false
    }
    
    private fun startPeriodicSync() {
        serviceScope.launch {
            while (isTrackingActive) {
                try {
                    delay(SYNC_INTERVAL)
                    
                    if (!isTrackingActive) break
                    
                    val result = locationRepository.syncUnsyncedLocations()
                    result.fold(
                        onSuccess = { syncedCount ->
                            if (syncedCount > 0) {
                                Timber.i("Synced $syncedCount locations with server")
                            }
                        },
                        onFailure = { exception ->
                            Timber.w(exception, "Failed to sync locations")
                        }
                    )
                    
                    // Cleanup old locations
                    locationRepository.cleanupOldLocations()
                    
                } catch (e: Exception) {
                    Timber.e(e, "Error in periodic sync")
                }
            }
        }
    }
    
    private fun createNotification(contentText: String = "Location tracking is active during duty"): Notification {
        val notificationIntent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this, 0, notificationIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        return NotificationCompat.Builder(this, PLSTravelsApplication.LOCATION_SERVICE_CHANNEL_ID)
            .setContentTitle("PLS Travels - Tracking Location")
            .setContentText(contentText)
            .setSmallIcon(R.drawable.ic_location_24) // Use custom icon
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setShowWhen(false)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setPriority(NotificationCompat.PRIORITY_LOW) // Low priority for battery optimization
            .build()
    }
    
    private fun updateNotification(title: String, text: String) {
        try {
            val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as android.app.NotificationManager
            val notification = createNotification(text)
            notificationManager.notify(PLSTravelsApplication.LOCATION_SERVICE_NOTIFICATION_ID, notification)
        } catch (e: Exception) {
            Timber.e(e, "Failed to update notification")
        }
    }
}