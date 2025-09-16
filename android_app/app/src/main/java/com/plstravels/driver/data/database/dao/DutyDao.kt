package com.plstravels.driver.data.database.dao

import androidx.room.*
import com.plstravels.driver.data.database.entity.DutyEntity

/**
 * Room DAO for duty operations
 */
@Dao
interface DutyDao {
    
    @Query("SELECT * FROM duties WHERE id = :dutyId")
    suspend fun getDutyById(dutyId: Int): DutyEntity?
    
    @Query("SELECT * FROM duties WHERE driverId = :driverId ORDER BY dutyDate DESC")
    suspend fun getDutiesByDriverId(driverId: Int): List<DutyEntity>
    
    @Query("SELECT * FROM duties WHERE driverId = :driverId AND dutyDate = :date")
    suspend fun getDutiesByDriverAndDate(driverId: Int, date: String): List<DutyEntity>
    
    @Query("SELECT * FROM duties WHERE status = :status")
    suspend fun getDutiesByStatus(status: String): List<DutyEntity>
    
    @Query("SELECT * FROM duties WHERE driverId = :driverId AND status = :status")
    suspend fun getDutiesByDriverAndStatus(driverId: Int, status: String): List<DutyEntity>
    
    @Query("SELECT * FROM duties WHERE isSynced = 0")
    suspend fun getUnsyncedDuties(): List<DutyEntity>
    
    @Query("SELECT * FROM duties ORDER BY dutyDate DESC, id DESC")
    suspend fun getAllDuties(): List<DutyEntity>
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertDuty(duty: DutyEntity)
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertDuties(duties: List<DutyEntity>)
    
    @Update
    suspend fun updateDuty(duty: DutyEntity)
    
    @Delete
    suspend fun deleteDuty(duty: DutyEntity)
    
    @Query("DELETE FROM duties WHERE id = :dutyId")
    suspend fun deleteDutyById(dutyId: Int)
    
    @Query("UPDATE duties SET isSynced = :isSynced WHERE id = :dutyId")
    suspend fun updateSyncStatus(dutyId: Int, isSynced: Boolean)
    
    @Query("UPDATE duties SET updatedAt = :timestamp WHERE id = :dutyId")
    suspend fun updateTimestamp(dutyId: Int, timestamp: Long = System.currentTimeMillis())
}