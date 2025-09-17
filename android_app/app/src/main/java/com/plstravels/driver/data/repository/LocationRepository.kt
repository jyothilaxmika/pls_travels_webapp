package com.plstravels.driver.data.repository

import com.plstravels.driver.data.api.DutyApi
import com.plstravels.driver.data.api.LocationUpdateRequest
import com.plstravels.driver.data.database.dao.LocationDao
import com.plstravels.driver.data.database.dao.UserDao
import com.plstravels.driver.data.database.entity.LocationEntity
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Repository for managing location data
 */
@Singleton
class LocationRepository @Inject constructor(
    private val locationDao: LocationDao,
    private val userDao: UserDao,
    private val dutyApi: DutyApi
) {

    /**
     * Save location to local database
     */
    suspend fun saveLocation(
        latitude: Double,
        longitude: Double,
        accuracy: Float,
        speed: Float,
        heading: Float
    ): Result<LocationEntity> {
        return try {
            // Get current driver ID
            val driverId = getCurrentDriverId()
            
            val locationEntity = LocationEntity(
                driverId = driverId,
                latitude = latitude,
                longitude = longitude,
                accuracy = accuracy,
                speed = speed,
                heading = heading,
                timestamp = System.currentTimeMillis(),
                isSynced = false
            )
            
            val locationId = locationDao.insertLocation(locationEntity)
            val savedLocation = locationEntity.copy(id = locationId)
            
            Timber.d("Location saved locally: $savedLocation")
            Result.success(savedLocation)
            
        } catch (e: Exception) {
            Timber.e(e, "Failed to save location")
            Result.failure(e)
        }
    }

    /**
     * Get recent locations for current driver
     */
    suspend fun getRecentLocations(limit: Int = 50): List<LocationEntity> {
        return try {
            val driverId = getCurrentDriverId()
            locationDao.getRecentLocationsByDriverId(driverId, limit)
        } catch (e: Exception) {
            Timber.e(e, "Failed to get recent locations")
            emptyList()
        }
    }

    /**
     * Get locations by time range
     */
    suspend fun getLocationsByTimeRange(
        startTime: Long,
        endTime: Long
    ): List<LocationEntity> {
        return try {
            val driverId = getCurrentDriverId()
            locationDao.getLocationsByDriverAndTimeRange(driverId, startTime, endTime)
        } catch (e: Exception) {
            Timber.e(e, "Failed to get locations by time range")
            emptyList()
        }
    }

    /**
     * Sync unsynced locations with server
     */
    suspend fun syncUnsyncedLocations(): Result<Int> {
        return try {
            val driverId = getCurrentDriverId()
            val unsyncedLocations = locationDao.getUnsyncedLocationsByDriverId(driverId)
            
            if (unsyncedLocations.isEmpty()) {
                Timber.d("No unsynced locations to sync")
                return Result.success(0)
            }
            
            var syncedCount = 0
            val locationIds = mutableListOf<Long>()
            
            for (location in unsyncedLocations) {
                try {
                    val request = LocationUpdateRequest(
                        latitude = location.latitude,
                        longitude = location.longitude,
                        accuracy = location.accuracy,
                        speed = location.speed,
                        heading = location.heading,
                        device_info = mapOf(
                            "timestamp" to location.timestamp,
                            "local_id" to location.id
                        )
                    )
                    
                    val response = dutyApi.updateLocation(request)
                    if (response.isSuccessful) {
                        locationIds.add(location.id)
                        syncedCount++
                        Timber.d("Location synced: ${location.id}")
                    } else {
                        Timber.w("Failed to sync location ${location.id}: ${response.code()}")
                    }
                    
                } catch (e: Exception) {
                    Timber.e(e, "Error syncing location ${location.id}")
                }
            }
            
            // Mark synced locations
            if (locationIds.isNotEmpty()) {
                locationDao.markLocationsSynced(locationIds)
                Timber.i("Marked $syncedCount locations as synced")
            }
            
            Result.success(syncedCount)
            
        } catch (e: Exception) {
            Timber.e(e, "Failed to sync locations")
            Result.failure(e)
        }
    }

    /**
     * Clean up old locations (keep last 7 days)
     */
    suspend fun cleanupOldLocations(): Result<Int> {
        return try {
            val driverId = getCurrentDriverId()
            val sevenDaysAgo = System.currentTimeMillis() - (7 * 24 * 60 * 60 * 1000L)
            
            // Only delete synced locations older than 7 days
            val oldLocationsCount = locationDao.getLocationsByDriverAndTimeRange(
                driverId, 0, sevenDaysAgo
            ).filter { it.isSynced }.size
            
            locationDao.deleteOldLocationsByDriverId(driverId, sevenDaysAgo)
            
            Timber.i("Cleaned up $oldLocationsCount old locations")
            Result.success(oldLocationsCount)
            
        } catch (e: Exception) {
            Timber.e(e, "Failed to cleanup old locations")
            Result.failure(e)
        }
    }

    /**
     * Get location statistics for current driver
     */
    suspend fun getLocationStats(): Flow<LocationStats> = flow {
        try {
            val driverId = getCurrentDriverId()
            val today = System.currentTimeMillis()
            val startOfDay = today - (today % (24 * 60 * 60 * 1000L))
            
            val todayLocations = locationDao.getLocationsByDriverAndTimeRange(
                driverId, startOfDay, today
            )
            
            val unsyncedCount = locationDao.getUnsyncedLocationsByDriverId(driverId).size
            
            val stats = LocationStats(
                totalLocationsToday = todayLocations.size,
                unsyncedCount = unsyncedCount,
                lastLocationTime = todayLocations.maxByOrNull { it.timestamp }?.timestamp,
                averageAccuracy = todayLocations.map { it.accuracy }.average().takeIf { !it.isNaN() } ?: 0.0
            )
            
            emit(stats)
            
        } catch (e: Exception) {
            Timber.e(e, "Failed to get location stats")
            emit(LocationStats())
        }
    }

    /**
     * Get current driver ID from user session
     */
    private suspend fun getCurrentDriverId(): Int {
        return userDao.getCurrentUser()?.id ?: throw IllegalStateException("No logged in user")
    }
}

/**
 * Location statistics data class
 */
data class LocationStats(
    val totalLocationsToday: Int = 0,
    val unsyncedCount: Int = 0,
    val lastLocationTime: Long? = null,
    val averageAccuracy: Double = 0.0
)