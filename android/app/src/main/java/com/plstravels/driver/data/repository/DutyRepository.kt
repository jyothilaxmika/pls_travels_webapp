package com.plstravels.driver.data.repository

import com.plstravels.driver.data.local.DutyDao
import com.plstravels.driver.data.local.VehicleDao
import com.plstravels.driver.data.models.*
import com.plstravels.driver.data.network.ApiService
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Repository for duty management operations
 * Handles offline-first duty operations with server sync
 */
@Singleton
class DutyRepository @Inject constructor(
    private val apiService: ApiService,
    private val dutyDao: DutyDao,
    private val vehicleDao: VehicleDao,
    private val commandQueueRepository: CommandQueueRepository
) {
    
    fun getAllDuties(): Flow<List<Duty>> = dutyDao.getAllDuties()
    
    fun getActiveDuty(): Flow<Duty?> = dutyDao.getAllDuties().map { duties ->
        duties.firstOrNull { it.status == "ACTIVE" }
    }
    
    fun getAvailableVehicles(): Flow<List<Vehicle>> = vehicleDao.getAvailableVehicles()
    
    suspend fun refreshDuties(): Result<List<Duty>> {
        return try {
            val response = apiService.getDriverDuties()
            
            if (response.isSuccessful && response.body()?.success == true) {
                val duties = response.body()!!.duties
                dutyDao.insertDuties(duties)
                Result.success(duties)
            } else {
                Result.failure(Exception("Failed to fetch duties: ${response.body()?.error}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun refreshVehicles(): Result<List<Vehicle>> {
        return try {
            val response = apiService.getAvailableVehicles()
            
            if (response.isSuccessful && response.body()?.success == true) {
                val vehicles = response.body()!!.vehicles
                vehicleDao.insertVehicles(vehicles)
                Result.success(vehicles)
            } else {
                Result.failure(Exception("Failed to fetch vehicles: ${response.body()?.error}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun startDuty(
        vehicleId: Int,
        startOdometer: Double,
        currentLocation: LocationData?
    ): Result<DutyDetails> {
        return try {
            // Get vehicle details for local duty creation
            val vehicle = vehicleDao.getVehicleById(vehicleId)
            
            // Generate temp ID for consistent tracking
            val tempDutyId = generateTempId()
            
            // Create local duty first (offline-first approach)
            val localDuty = Duty(
                id = tempDutyId.hashCode(), // Convert string to int for Duty ID
                status = "ACTIVE",
                startTime = System.currentTimeMillis(),
                endTime = null,
                vehicle = vehicle,
                route = null,
                totalEarnings = 0.0,
                distanceKm = 0.0,
                createdAt = System.currentTimeMillis()
            )
            dutyDao.insertDuty(localDuty)
            
            // Queue command for server sync with proper temp ID tracking
            val command = StartDutyCommand(
                vehicleId = vehicleId,
                startOdometer = startOdometer.toInt(),
                notes = "Started duty from mobile app",
                tempDutyId = tempDutyId
            )
            commandQueueRepository.queueCommand(
                command = command,
                idempotencyKey = command.idempotencyKey,
                tempEntityId = tempDutyId
            )
            
            // Create local duty details for immediate UI update
            val dutyDetails = DutyDetails(
                id = localDuty.id,
                status = localDuty.status,
                startTime = localDuty.startTime,
                endTime = null,
                vehicle = vehicle,
                distanceKm = 0.0,
                totalRevenue = 0.0
            )
            
            Result.success(dutyDetails)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    private fun generateTempId(): String {
        // Generate temporary negative ID for offline duties as string
        // Server will assign proper positive ID when synced
        return "temp_${System.currentTimeMillis()}"
    }
    
    suspend fun endDuty(
        dutyId: Int?,
        endOdometer: Double,
        totalRevenue: Double,
        currentLocation: LocationData?,
        notes: String
    ): Result<DutyDetails> {
        return try {
            // Get current active duty
            val currentDuty = dutyDao.getActiveDuty()
            if (currentDuty == null) {
                return Result.failure(Exception("No active duty found"))
            }
            
            // Update local duty first (offline-first approach)
            val updatedDuty = currentDuty.copy(
                status = "COMPLETED",
                endTime = System.currentTimeMillis(),
                totalEarnings = totalRevenue,
                distanceKm = endOdometer - (currentDuty.vehicle?.mileage ?: 0.0)
            )
            dutyDao.updateDuty(updatedDuty)
            
            // Queue command for server sync
            val command = EndDutyCommand(
                dutyId = currentDuty.id,
                endOdometer = endOdometer.toInt(),
                notes = notes
            )
            commandQueueRepository.queueCommand(
                command = command,
                idempotencyKey = command.idempotencyKey,
                tempEntityId = currentDuty.id.toString()
            )
            
            // Create duty details for immediate UI update
            val dutyDetails = DutyDetails(
                id = updatedDuty.id,
                status = updatedDuty.status,
                startTime = updatedDuty.startTime,
                endTime = updatedDuty.endTime,
                vehicle = updatedDuty.vehicle,
                distanceKm = updatedDuty.distanceKm,
                totalRevenue = updatedDuty.totalEarnings
            )
            
            Result.success(dutyDetails)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun getCurrentActiveDuty(): Duty? {
        return dutyDao.getActiveDuty()
    }
}