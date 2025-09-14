package com.plstravels.driver.data.repository

import com.plstravels.driver.data.local.LocationDao
import com.plstravels.driver.data.models.*
import com.plstravels.driver.data.network.ApiService
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import android.location.Location
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Repository for location data management and synchronization
 * Handles offline-first location tracking with server sync
 */
@Singleton
class LocationRepository @Inject constructor(
    private val apiService: ApiService,
    private val locationDao: LocationDao
) {
    
    fun getLocationPointsForDuty(dutyId: Int): Flow<List<LocationPoint>> {
        return locationDao.getLocationPointsForDuty(dutyId)
    }
    
    fun getAllLocationSessions(): Flow<List<LocationSession>> {
        return locationDao.getAllLocationSessions()
    }
    
    fun getActiveLocationSession(): Flow<LocationSession?> {
        return locationDao.getAllLocationSessions().map { sessions ->
            sessions.firstOrNull { it.isActive }
        }
    }
    
    suspend fun startLocationSession(dutyId: Int): Result<Long> {
        return try {
            val session = LocationSession(
                dutyId = dutyId,
                startTime = System.currentTimeMillis(),
                isActive = true
            )
            val sessionId = locationDao.insertLocationSession(session)
            Result.success(sessionId)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun endLocationSession(dutyId: Int): Result<LocationSession?> {
        return try {
            val session = locationDao.getLocationSessionForDuty(dutyId)
            if (session != null && session.isActive) {
                locationDao.endLocationSession(session.id, System.currentTimeMillis())
                val updatedSession = session.copy(
                    endTime = System.currentTimeMillis(),
                    isActive = false
                )
                Result.success(updatedSession)
            } else {
                Result.success(null)
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun insertLocationPoint(locationPoint: LocationPoint): Result<Long> {
        return try {
            val id = locationDao.insertLocationPoint(locationPoint)
            Result.success(id)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Sync pending location points to server
     * Returns number of successfully synced points
     */
    suspend fun syncPendingLocations(): Result<Int> {
        return try {
            val unsyncedPoints = locationDao.getUnsyncedLocationPoints(50) // Batch size
            
            if (unsyncedPoints.isEmpty()) {
                return Result.success(0)
            }
            
            // Convert to API format
            val locationUpdates = unsyncedPoints.map { point ->
                LocationUpdate(
                    latitude = point.latitude,
                    longitude = point.longitude,
                    accuracy = point.accuracy,
                    timestamp = point.timestamp,
                    dutyId = point.dutyId,
                    speed = point.speed,
                    bearing = point.bearing
                )
            }
            
            // Send to server
            val response = apiService.uploadLocation(locationUpdates)
            
            if (response.isSuccessful && response.body()?.success == true) {
                // Mark as synced
                val pointIds = unsyncedPoints.map { it.id }
                locationDao.markLocationPointsAsSynced(pointIds)
                
                // Clean up old synced points (older than 7 days) and failed retries
                val cutoffTime = System.currentTimeMillis() - (7 * 24 * 60 * 60 * 1000L)
                locationDao.deleteOldSyncedLocationPoints(cutoffTime)
                locationDao.deleteFailedSyncLocationPoints(cutoffTime = cutoffTime)
                
                Result.success(unsyncedPoints.size)
            } else {
                // Increment retry count for failed points
                val pointIds = unsyncedPoints.map { it.id }
                locationDao.incrementSyncRetryCount(pointIds)
                
                Result.failure(Exception("Sync failed: ${response.body()?.error ?: "Unknown error"}"))
            }
            
        } catch (e: Exception) {
            // Increment retry count for network errors
            val unsyncedPoints = locationDao.getUnsyncedLocationPoints(50)
            if (unsyncedPoints.isNotEmpty()) {
                val pointIds = unsyncedPoints.map { it.id }
                locationDao.incrementSyncRetryCount(pointIds)
            }
            
            Result.failure(e)
        }
    }
    
    suspend fun getUnsyncedLocationCount(): Int {
        return locationDao.getUnsyncedCount()
    }
    
    suspend fun getLocationStatsForDuty(dutyId: Int): LocationStats {
        return try {
            // Get location points directly as a list for calculations
            val points = locationDao.getLocationPointsListForDuty(dutyId)
            
            if (points.isEmpty()) {
                return LocationStats.empty()
            }
            
            // Sort points by timestamp to ensure proper order
            val sortedPoints = points.sortedBy { it.timestamp }
            
            // Calculate total distance
            var totalDistance = 0.0
            var maxSpeed = 0.0
            var totalSpeed = 0.0
            var speedCount = 0
            
            for (i in 1 until sortedPoints.size) {
                val currentPoint = sortedPoints[i]
                val previousPoint = sortedPoints[i - 1]
                
                // Calculate distance between consecutive points
                val location1 = Location("").apply {
                    latitude = previousPoint.latitude
                    longitude = previousPoint.longitude
                }
                val location2 = Location("").apply {
                    latitude = currentPoint.latitude
                    longitude = currentPoint.longitude
                }
                
                val distance = location1.distanceTo(location2).toDouble()
                totalDistance += distance
                
                // Track speed statistics
                currentPoint.speed?.let { speed ->
                    maxSpeed = maxOf(maxSpeed, speed.toDouble())
                    totalSpeed += speed.toDouble()
                    speedCount++
                }
            }
            
            // Calculate average speed
            val averageSpeed = if (speedCount > 0) totalSpeed / speedCount else 0.0
            
            // Get start and end times
            val startTime = sortedPoints.first().timestamp
            val endTime = sortedPoints.last().timestamp
            
            LocationStats(
                totalDistance = totalDistance,
                totalPoints = points.size,
                startTime = startTime,
                endTime = endTime,
                averageSpeed = averageSpeed,
                maxSpeed = maxSpeed
            )
            
        } catch (e: Exception) {
            // Return empty stats on error
            LocationStats.empty()
        }
    }
    
    suspend fun deleteLocationDataForDuty(dutyId: Int): Result<Unit> {
        return try {
            locationDao.deleteLocationPointsForDuty(dutyId)
            locationDao.deleteLocationSessionForDuty(dutyId)
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun deleteSyncedLocationDataForDuty(dutyId: Int): Result<Unit> {
        return try {
            locationDao.deleteSyncedLocationPointsForDuty(dutyId)
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun resetSyncStatusForDuty(dutyId: Int): Result<Unit> {
        return try {
            locationDao.resetSyncStatusForDuty(dutyId)
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun getCleanupStats(): Triple<Int, Int, Int> {
        return try {
            val cutoffTime = System.currentTimeMillis() - (7 * 24 * 60 * 60 * 1000L)
            val oldSyncedCount = locationDao.countOldSyncedLocationPoints(cutoffTime)
            val unsyncedCount = locationDao.getUnsyncedCount()
            val totalCount = oldSyncedCount + unsyncedCount
            Triple(totalCount, oldSyncedCount, unsyncedCount)
        } catch (e: Exception) {
            Triple(0, 0, 0)
        }
    }
}

/**
 * Location statistics for a duty
 */
data class LocationStats(
    val totalDistance: Double,
    val totalPoints: Int,
    val startTime: Long?,
    val endTime: Long?,
    val averageSpeed: Double,
    val maxSpeed: Double
) {
    companion object {
        fun empty() = LocationStats(
            totalDistance = 0.0,
            totalPoints = 0,
            startTime = null,
            endTime = null,
            averageSpeed = 0.0,
            maxSpeed = 0.0
        )
    }
}