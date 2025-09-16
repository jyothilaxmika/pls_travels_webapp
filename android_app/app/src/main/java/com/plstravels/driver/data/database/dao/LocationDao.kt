package com.plstravels.driver.data.database.dao

import androidx.room.*
import com.plstravels.driver.data.database.entity.LocationEntity

/**
 * Room DAO for location operations
 */
@Dao
interface LocationDao {
    
    @Query("SELECT * FROM locations WHERE id = :locationId")
    suspend fun getLocationById(locationId: Long): LocationEntity?
    
    @Query("SELECT * FROM locations WHERE driverId = :driverId ORDER BY timestamp DESC")
    suspend fun getLocationsByDriverId(driverId: Int): List<LocationEntity>
    
    @Query("SELECT * FROM locations WHERE driverId = :driverId AND timestamp >= :startTime AND timestamp <= :endTime ORDER BY timestamp ASC")
    suspend fun getLocationsByDriverAndTimeRange(driverId: Int, startTime: Long, endTime: Long): List<LocationEntity>
    
    @Query("SELECT * FROM locations WHERE driverId = :driverId ORDER BY timestamp DESC LIMIT :limit")
    suspend fun getRecentLocationsByDriverId(driverId: Int, limit: Int = 50): List<LocationEntity>
    
    @Query("SELECT * FROM locations WHERE isSynced = 0")
    suspend fun getUnsyncedLocations(): List<LocationEntity>
    
    @Query("SELECT * FROM locations WHERE driverId = :driverId AND isSynced = 0")
    suspend fun getUnsyncedLocationsByDriverId(driverId: Int): List<LocationEntity>
    
    @Query("SELECT * FROM locations ORDER BY timestamp DESC")
    suspend fun getAllLocations(): List<LocationEntity>
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertLocation(location: LocationEntity): Long
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertLocations(locations: List<LocationEntity>): List<Long>
    
    @Update
    suspend fun updateLocation(location: LocationEntity)
    
    @Delete
    suspend fun deleteLocation(location: LocationEntity)
    
    @Query("DELETE FROM locations WHERE id = :locationId")
    suspend fun deleteLocationById(locationId: Long)
    
    @Query("DELETE FROM locations WHERE driverId = :driverId AND timestamp < :beforeTimestamp")
    suspend fun deleteOldLocationsByDriverId(driverId: Int, beforeTimestamp: Long)
    
    @Query("UPDATE locations SET isSynced = :isSynced WHERE id = :locationId")
    suspend fun updateSyncStatus(locationId: Long, isSynced: Boolean)
    
    @Query("UPDATE locations SET isSynced = 1 WHERE id IN (:locationIds)")
    suspend fun markLocationsSynced(locationIds: List<Long>)
}