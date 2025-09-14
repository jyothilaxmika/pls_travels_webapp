package com.plstravels.driver.data.local

import androidx.room.*
import com.plstravels.driver.data.models.LocationPoint
import com.plstravels.driver.data.models.LocationSession
import kotlinx.coroutines.flow.Flow

/**
 * Room DAO for location data management
 */
@Dao
interface LocationDao {
    
    // Location Points
    @Query("SELECT * FROM location_points ORDER BY timestamp DESC")
    fun getAllLocationPoints(): Flow<List<LocationPoint>>
    
    @Query("SELECT * FROM location_points WHERE dutyId = :dutyId ORDER BY timestamp ASC")
    fun getLocationPointsForDuty(dutyId: Int): Flow<List<LocationPoint>>
    
    @Query("SELECT * FROM location_points WHERE dutyId = :dutyId ORDER BY timestamp ASC")
    suspend fun getLocationPointsListForDuty(dutyId: Int): List<LocationPoint>
    
    @Query("SELECT * FROM location_points WHERE isSynced = 0 ORDER BY timestamp ASC LIMIT :limit")
    suspend fun getUnsyncedLocationPoints(limit: Int = 50): List<LocationPoint>
    
    @Query("SELECT COUNT(*) FROM location_points WHERE isSynced = 0")
    suspend fun getUnsyncedCount(): Int
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertLocationPoint(locationPoint: LocationPoint): Long
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertLocationPoints(locationPoints: List<LocationPoint>)
    
    @Query("UPDATE location_points SET isSynced = 1 WHERE id IN (:ids)")
    suspend fun markLocationPointsAsSynced(ids: List<Long>)
    
    @Query("UPDATE location_points SET syncRetryCount = syncRetryCount + 1 WHERE id IN (:ids)")
    suspend fun incrementSyncRetryCount(ids: List<Long>)
    
    // Cleanup operations - use createdAt for database insertion time, timestamp for GPS time
    @Query("DELETE FROM location_points WHERE isSynced = 1 AND createdAt < :cutoffTime")
    suspend fun deleteOldSyncedLocationPoints(cutoffTime: Long)
    
    @Query("DELETE FROM location_points WHERE syncRetryCount > :maxRetries AND createdAt < :cutoffTime")
    suspend fun deleteFailedSyncLocationPoints(maxRetries: Int = 5, cutoffTime: Long)
    
    @Query("SELECT COUNT(*) FROM location_points WHERE isSynced = 1 AND createdAt < :cutoffTime")
    suspend fun countOldSyncedLocationPoints(cutoffTime: Long): Int
    
    // Location Sessions
    @Query("SELECT * FROM location_sessions ORDER BY startTime DESC")
    fun getAllLocationSessions(): Flow<List<LocationSession>>
    
    @Query("SELECT * FROM location_sessions WHERE dutyId = :dutyId")
    suspend fun getLocationSessionForDuty(dutyId: Int): LocationSession?
    
    @Query("SELECT * FROM location_sessions WHERE isActive = 1 LIMIT 1")
    suspend fun getActiveLocationSession(): LocationSession?
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertLocationSession(session: LocationSession): Long
    
    @Update
    suspend fun updateLocationSession(session: LocationSession)
    
    @Query("UPDATE location_sessions SET isActive = 0, endTime = :endTime WHERE id = :sessionId")
    suspend fun endLocationSession(sessionId: Long, endTime: Long)
    
    @Query("UPDATE location_sessions SET totalDistance = :distance, totalPoints = :points WHERE id = :sessionId")
    suspend fun updateLocationSessionStats(sessionId: Long, distance: Double, points: Int)
    
    // Duty-specific cleanup operations
    @Query("DELETE FROM location_points WHERE dutyId = :dutyId")
    suspend fun deleteLocationPointsForDuty(dutyId: Int)
    
    @Query("DELETE FROM location_points WHERE dutyId = :dutyId AND isSynced = 1")
    suspend fun deleteSyncedLocationPointsForDuty(dutyId: Int)
    
    @Query("UPDATE location_points SET isSynced = 0, syncRetryCount = 0 WHERE dutyId = :dutyId")
    suspend fun resetSyncStatusForDuty(dutyId: Int)
    
    @Query("DELETE FROM location_sessions WHERE dutyId = :dutyId")
    suspend fun deleteLocationSessionForDuty(dutyId: Int)
}