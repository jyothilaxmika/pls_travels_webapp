package com.plstravels.driver.data.local

import androidx.room.*
import com.plstravels.driver.data.models.Duty
import kotlinx.coroutines.flow.Flow

/**
 * Room DAO for duty management
 */
@Dao
interface DutyDao {
    
    @Query("SELECT * FROM duties ORDER BY created_at DESC")
    fun getAllDuties(): Flow<List<Duty>>
    
    @Query("SELECT * FROM duties WHERE status = :status ORDER BY created_at DESC")
    fun getDutiesByStatus(status: String): Flow<List<Duty>>
    
    @Query("SELECT * FROM duties WHERE id = :dutyId")
    suspend fun getDutyById(dutyId: Int): Duty?
    
    @Query("SELECT * FROM duties WHERE status = 'ACTIVE' LIMIT 1")
    suspend fun getActiveDuty(): Duty?
    
    @Query("SELECT * FROM duties WHERE syncStatus = 'PENDING'")
    suspend fun getPendingSyncDuties(): List<Duty>
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertDuty(duty: Duty)
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertDuties(duties: List<Duty>)
    
    @Update
    suspend fun updateDuty(duty: Duty)
    
    @Query("UPDATE duties SET syncStatus = :syncStatus WHERE id = :dutyId")
    suspend fun updateSyncStatus(dutyId: Int, syncStatus: String)
    
    @Delete
    suspend fun deleteDuty(duty: Duty)
    
    @Query("DELETE FROM duties WHERE isLocalOnly = 1 AND syncStatus = 'SYNCED'")
    suspend fun deleteLocalSyncedDuties()
}