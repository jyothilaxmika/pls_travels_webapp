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
    private val vehicleDao: VehicleDao
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
            val request = StartDutyRequest(
                vehicleId = vehicleId,
                startOdometer = startOdometer,
                startLocation = currentLocation
            )
            
            val response = apiService.startDuty(request)
            
            if (response.isSuccessful && response.body()?.success == true) {
                val dutyDetails = response.body()!!.duty!!
                
                // Convert to local Duty model and save
                val duty = Duty(
                    id = dutyDetails.id,
                    status = dutyDetails.status,
                    startTime = dutyDetails.startTime,
                    endTime = dutyDetails.endTime,
                    vehicle = dutyDetails.vehicle,
                    route = null,
                    totalEarnings = 0.0,
                    distanceKm = dutyDetails.distanceKm,
                    createdAt = dutyDetails.startTime
                )
                dutyDao.insertDuty(duty)
                
                Result.success(dutyDetails)
            } else {
                Result.failure(Exception("Failed to start duty: ${response.body()?.error}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun endDuty(
        dutyId: Int?,
        endOdometer: Double,
        totalRevenue: Double,
        currentLocation: LocationData?,
        notes: String
    ): Result<DutyDetails> {
        return try {
            val request = EndDutyRequest(
                dutyId = dutyId,
                endOdometer = endOdometer,
                totalRevenue = totalRevenue,
                endLocation = currentLocation,
                notes = notes
            )
            
            val response = apiService.endDuty(request)
            
            if (response.isSuccessful && response.body()?.success == true) {
                val dutyDetails = response.body()!!.duty!!
                
                // Update local duty
                val duty = Duty(
                    id = dutyDetails.id,
                    status = dutyDetails.status,
                    startTime = dutyDetails.startTime,
                    endTime = dutyDetails.endTime,
                    vehicle = dutyDetails.vehicle,
                    route = null,
                    totalEarnings = dutyDetails.totalRevenue,
                    distanceKm = dutyDetails.distanceKm,
                    createdAt = dutyDetails.startTime
                )
                dutyDao.updateDuty(duty)
                
                Result.success(dutyDetails)
            } else {
                Result.failure(Exception("Failed to end duty: ${response.body()?.error}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun getCurrentActiveDuty(): Duty? {
        return dutyDao.getActiveDuty()
    }
}