package com.plstravels.driver.data.repository

import com.plstravels.driver.data.local.LocationDao
import com.plstravels.driver.data.models.*
import com.plstravels.driver.data.network.ApiService
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
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
                
                // Clean up old synced points (older than 7 days)
                val cutoffTime = System.currentTimeMillis() - (7 * 24 * 60 * 60 * 1000L)
                locationDao.deleteOldSyncedLocationPoints(cutoffTime)
                
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
        val points = locationDao.getLocationPointsForDuty(dutyId)
        return LocationStats.empty() // TODO: Calculate from points flow
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