package com.plstravels.driver.data.database.dao

import androidx.room.*
import com.plstravels.driver.data.database.entity.VehicleEntity

/**
 * Room DAO for vehicle operations
 */
@Dao
interface VehicleDao {
    
    @Query("SELECT * FROM vehicles WHERE id = :vehicleId")
    suspend fun getVehicleById(vehicleId: Int): VehicleEntity?
    
    @Query("SELECT * FROM vehicles WHERE registrationNumber = :registrationNumber")
    suspend fun getVehicleByRegistrationNumber(registrationNumber: String): VehicleEntity?
    
    @Query("SELECT * FROM vehicles WHERE isAvailable = 1")
    suspend fun getAvailableVehicles(): List<VehicleEntity>
    
    @Query("SELECT * FROM vehicles")
    suspend fun getAllVehicles(): List<VehicleEntity>
    
    @Query("SELECT * FROM vehicles")
    fun getAllVehiclesSync(): List<VehicleEntity>
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertVehicle(vehicle: VehicleEntity)
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertVehicles(vehicles: List<VehicleEntity>)
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(vehicles: List<VehicleEntity>)
    
    @Update
    suspend fun updateVehicle(vehicle: VehicleEntity)
    
    @Delete
    suspend fun deleteVehicle(vehicle: VehicleEntity)
    
    @Query("DELETE FROM vehicles WHERE id = :vehicleId")
    suspend fun deleteVehicleById(vehicleId: Int)
    
    @Query("UPDATE vehicles SET currentOdometer = :odometer, updatedAt = :timestamp WHERE id = :vehicleId")
    suspend fun updateOdometer(vehicleId: Int, odometer: Double, timestamp: Long = System.currentTimeMillis())
    
    @Query("UPDATE vehicles SET isAvailable = :isAvailable, updatedAt = :timestamp WHERE id = :vehicleId")
    suspend fun updateAvailability(vehicleId: Int, isAvailable: Boolean, timestamp: Long = System.currentTimeMillis())
    
    @Query("UPDATE vehicles SET updatedAt = :timestamp WHERE id = :vehicleId")
    suspend fun updateTimestamp(vehicleId: Int, timestamp: Long = System.currentTimeMillis())
}