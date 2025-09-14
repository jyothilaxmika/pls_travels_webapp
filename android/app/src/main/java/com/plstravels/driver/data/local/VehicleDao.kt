package com.plstravels.driver.data.local

import androidx.room.*
import com.plstravels.driver.data.models.Vehicle
import kotlinx.coroutines.flow.Flow

/**
 * Room DAO for vehicle management
 */
@Dao
interface VehicleDao {
    
    @Query("SELECT * FROM vehicles ORDER BY registration_number")
    fun getAllVehicles(): Flow<List<Vehicle>>
    
    @Query("SELECT * FROM vehicles WHERE is_available = 1 ORDER BY registration_number")
    fun getAvailableVehicles(): Flow<List<Vehicle>>
    
    @Query("SELECT * FROM vehicles WHERE id = :vehicleId")
    suspend fun getVehicleById(vehicleId: Int): Vehicle?
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertVehicle(vehicle: Vehicle)
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertVehicles(vehicles: List<Vehicle>)
    
    @Update
    suspend fun updateVehicle(vehicle: Vehicle)
    
    @Delete
    suspend fun deleteVehicle(vehicle: Vehicle)
    
    @Query("DELETE FROM vehicles")
    suspend fun deleteAllVehicles()
}