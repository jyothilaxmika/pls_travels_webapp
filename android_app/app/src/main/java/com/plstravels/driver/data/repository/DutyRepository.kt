package com.plstravels.driver.data.repository

import com.plstravels.driver.data.api.DutyApi
import com.plstravels.driver.data.database.AppDatabase
import com.plstravels.driver.data.database.dao.DutyDao
import com.plstravels.driver.data.database.dao.VehicleDao
import com.plstravels.driver.data.database.entity.DutyEntity
import com.plstravels.driver.data.database.entity.VehicleEntity
import com.plstravels.driver.data.model.*
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Repository for duty management operations
 * Handles both online API calls and offline Room database storage
 */
@Singleton
class DutyRepository @Inject constructor(
    private val dutyApi: DutyApi,
    private val dutyDao: DutyDao,
    private val vehicleDao: VehicleDao,
    private val database: AppDatabase
) {

    /**
     * Get duties from local database
     */
    fun getDutiesFlow(): Flow<List<DutyEntity>> {
        return dutyDao.getAllDuties()
    }

    /**
     * Get duties with sync from API
     */
    suspend fun getDuties(forceRefresh: Boolean = false): Result<List<Duty>> {
        return try {
            if (forceRefresh) {
                // Fetch from API and update local database
                val response = dutyApi.getDuties()
                if (response.isSuccessful && response.body()?.success == true) {
                    val duties = response.body()?.data ?: emptyList()
                    // Update local database
                    updateLocalDuties(duties)
                    Result.success(duties)
                } else {
                    // Fallback to local data
                    val localDuties = dutyDao.getAllDutiesSync()
                    Result.success(localDuties.map { it.toDomainModel() })
                }
            } else {
                // Return local data
                val localDuties = dutyDao.getAllDutiesSync()
                Result.success(localDuties.map { it.toDomainModel() })
            }
        } catch (e: Exception) {
            Timber.e(e, "Failed to get duties")
            // Fallback to local data
            val localDuties = dutyDao.getAllDutiesSync()
            Result.success(localDuties.map { it.toDomainModel() })
        }
    }

    /**
     * Get available vehicles
     */
    suspend fun getAvailableVehicles(forceRefresh: Boolean = false): Result<List<Vehicle>> {
        return try {
            if (forceRefresh) {
                val response = dutyApi.getAvailableVehicles()
                if (response.isSuccessful && response.body()?.success == true) {
                    val vehicles = response.body()?.data ?: emptyList()
                    // Update local database
                    updateLocalVehicles(vehicles)
                    Result.success(vehicles)
                } else {
                    // Fallback to local data
                    val localVehicles = vehicleDao.getAllVehiclesSync()
                    Result.success(localVehicles.map { it.toDomainModel() })
                }
            } else {
                // Return local data
                val localVehicles = vehicleDao.getAllVehiclesSync()
                Result.success(localVehicles.map { it.toDomainModel() })
            }
        } catch (e: Exception) {
            Timber.e(e, "Failed to get vehicles")
            // Fallback to local data
            val localVehicles = vehicleDao.getAllVehiclesSync()
            Result.success(localVehicles.map { it.toDomainModel() })
        }
    }

    /**
     * Start a new duty
     */
    suspend fun startDuty(request: DutyStartRequest): Result<Duty> {
        return try {
            // Try API first
            val response = dutyApi.startDuty(request)
            if (response.isSuccessful && response.body()?.success == true) {
                val duty = response.body()?.data!!
                // Save to local database
                saveDutyLocally(duty, isSynced = true)
                Result.success(duty)
            } else {
                // Create offline duty
                val offlineDuty = createOfflineDuty(request)
                saveDutyLocally(offlineDuty, isSynced = false)
                Result.success(offlineDuty)
            }
        } catch (e: Exception) {
            Timber.e(e, "Failed to start duty online, creating offline")
            // Create offline duty
            val offlineDuty = createOfflineDuty(request)
            saveDutyLocally(offlineDuty, isSynced = false)
            Result.success(offlineDuty)
        }
    }

    /**
     * End an active duty
     */
    suspend fun endDuty(request: DutyEndRequest): Result<Duty> {
        return try {
            // Try API first
            val response = dutyApi.endDuty(request)
            if (response.isSuccessful && response.body()?.success == true) {
                val duty = response.body()?.data!!
                // Update local database
                saveDutyLocally(duty, isSynced = true)
                Result.success(duty)
            } else {
                // Update offline duty
                val offlineDuty = updateOfflineDuty(request)
                if (offlineDuty != null) {
                    saveDutyLocally(offlineDuty, isSynced = false)
                    Result.success(offlineDuty)
                } else {
                    Result.failure(Exception("Duty not found"))
                }
            }
        } catch (e: Exception) {
            Timber.e(e, "Failed to end duty online, updating offline")
            // Update offline duty
            val offlineDuty = updateOfflineDuty(request)
            if (offlineDuty != null) {
                saveDutyLocally(offlineDuty, isSynced = false)
                Result.success(offlineDuty)
            } else {
                Result.failure(e)
            }
        }
    }

    /**
     * Get active duty
     */
    suspend fun getActiveDuty(): DutyEntity? {
        return dutyDao.getActiveDuty()
    }

    /**
     * Get active duty as Flow (reactive)
     */
    fun getActiveDutyFlow(): Flow<DutyEntity?> {
        return dutyDao.getActiveDutyFlow()
    }

    /**
     * Sync offline duties with server
     */
    suspend fun syncOfflineDuties(): Result<Int> {
        return try {
            val unsyncedDuties = dutyDao.getUnsyncedDuties()
            var syncedCount = 0
            
            for (dutyEntity in unsyncedDuties) {
                try {
                    val success = when (dutyEntity.status) {
                        "ACTIVE" -> {
                            // This is a duty start that needs to be synced
                            val startRequest = DutyStartRequest(
                                vehicleId = dutyEntity.vehicleId ?: 0,
                                startOdometer = dutyEntity.startOdometer ?: 0.0,
                                startFuelLevel = dutyEntity.startFuelLevel ?: 0.0,
                                latitude = dutyEntity.startLocationLat,
                                longitude = dutyEntity.startLocationLng,
                                photoUrl = dutyEntity.startPhotoUrl,
                                notes = dutyEntity.notes
                            )
                            
                            val response = dutyApi.startDuty(startRequest)
                            if (response.isSuccessful && response.body()?.success == true) {
                                // Update local duty with server ID
                                val serverDuty = response.body()?.data!!
                                val updatedEntity = dutyEntity.copy(
                                    id = serverDuty.id,
                                    isSynced = true,
                                    updatedAt = System.currentTimeMillis()
                                )
                                dutyDao.updateDuty(updatedEntity)
                                true
                            } else {
                                false
                            }
                        }
                        
                        "COMPLETED" -> {
                            // This is a duty end that needs to be synced
                            val endRequest = DutyEndRequest(
                                dutyId = dutyEntity.id,
                                endOdometer = dutyEntity.endOdometer ?: 0.0,
                                endFuelLevel = dutyEntity.endFuelLevel ?: 0.0,
                                totalRevenue = dutyEntity.totalRevenue ?: 0.0,
                                totalTrips = dutyEntity.totalTrips ?: 0,
                                latitude = dutyEntity.endLocationLat,
                                longitude = dutyEntity.endLocationLng,
                                photoUrl = dutyEntity.endPhotoUrl,
                                notes = dutyEntity.notes
                            )
                            
                            val response = dutyApi.endDuty(endRequest)
                            if (response.isSuccessful && response.body()?.success == true) {
                                dutyDao.markAsSynced(dutyEntity.id)
                                true
                            } else {
                                false
                            }
                        }
                        
                        else -> {
                            Timber.w("Unknown duty status: ${dutyEntity.status}")
                            false
                        }
                    }
                    
                    if (success) {
                        syncedCount++
                        Timber.d("Successfully synced duty ${dutyEntity.id}")
                    }
                } catch (e: Exception) {
                    Timber.e(e, "Failed to sync duty ${dutyEntity.id}")
                }
            }
            
            Result.success(syncedCount)
        } catch (e: Exception) {
            Timber.e(e, "Failed to sync offline duties")
            Result.failure(e)
        }
    }

    private suspend fun updateLocalDuties(duties: List<Duty>) {
        val entities = duties.map { it.toEntity(isSynced = true) }
        dutyDao.insertAll(entities)
    }

    private suspend fun updateLocalVehicles(vehicles: List<Vehicle>) {
        val entities = vehicles.map { it.toEntity() }
        vehicleDao.insertAll(entities)
    }

    private suspend fun saveDutyLocally(duty: Duty, isSynced: Boolean) {
        val entity = duty.toEntity(isSynced = isSynced)
        dutyDao.insert(entity)
    }

    private fun createOfflineDuty(request: DutyStartRequest): Duty {
        val currentTime = System.currentTimeMillis()
        return Duty(
            id = -currentTime.toInt(), // Negative ID for offline duties
            driverId = 0, // Will be set from current user
            vehicleId = request.vehicleId,
            vehicle = null,
            dutyDate = java.time.LocalDate.now().toString(),
            startTime = java.time.LocalDateTime.now().toString(),
            endTime = null,
            startOdometer = request.startOdometer,
            endOdometer = null,
            startFuelLevel = request.startFuelLevel,
            endFuelLevel = null,
            status = "ACTIVE",
            totalRevenue = null,
            totalTrips = null,
            earnings = null,
            startPhotoUrl = request.photoUrl,
            endPhotoUrl = null,
            startLocationLat = request.latitude,
            startLocationLng = request.longitude,
            endLocationLat = null,
            endLocationLng = null,
            notes = request.notes,
            createdAt = java.time.LocalDateTime.now().toString(),
            updatedAt = java.time.LocalDateTime.now().toString()
        )
    }

    private suspend fun updateOfflineDuty(request: DutyEndRequest): Duty? {
        val existingDuty = dutyDao.getDutyById(request.dutyId)
        return existingDuty?.let { entity ->
            entity.toDomainModel().copy(
                endTime = java.time.LocalDateTime.now().toString(),
                endOdometer = request.endOdometer,
                endFuelLevel = request.endFuelLevel,
                totalRevenue = request.totalRevenue,
                totalTrips = request.totalTrips,
                status = "COMPLETED",
                endPhotoUrl = request.photoUrl,
                endLocationLat = request.latitude,
                endLocationLng = request.longitude,
                notes = request.notes,
                updatedAt = java.time.LocalDateTime.now().toString()
            )
        }
    }
}

// Extension functions for entity/domain model conversion
private fun Duty.toEntity(isSynced: Boolean = true): DutyEntity {
    return DutyEntity(
        id = id,
        driverId = driverId,
        vehicleId = vehicleId,
        dutyDate = dutyDate,
        startTime = startTime,
        endTime = endTime,
        startOdometer = startOdometer,
        endOdometer = endOdometer,
        startFuelLevel = startFuelLevel,
        endFuelLevel = endFuelLevel,
        status = status,
        totalRevenue = totalRevenue,
        totalTrips = totalTrips,
        earnings = earnings,
        startPhotoUrl = startPhotoUrl,
        endPhotoUrl = endPhotoUrl,
        startLocationLat = startLocationLat,
        startLocationLng = startLocationLng,
        endLocationLat = endLocationLat,
        endLocationLng = endLocationLng,
        notes = notes,
        isSynced = isSynced
    )
}

private fun DutyEntity.toDomainModel(): Duty {
    return Duty(
        id = id,
        driverId = driverId,
        vehicleId = vehicleId,
        vehicle = null, // Will be populated if needed
        dutyDate = dutyDate,
        startTime = startTime,
        endTime = endTime,
        startOdometer = startOdometer,
        endOdometer = endOdometer,
        startFuelLevel = startFuelLevel,
        endFuelLevel = endFuelLevel,
        status = status,
        totalRevenue = totalRevenue,
        totalTrips = totalTrips,
        earnings = earnings,
        startPhotoUrl = startPhotoUrl,
        endPhotoUrl = endPhotoUrl,
        startLocationLat = startLocationLat,
        startLocationLng = startLocationLng,
        endLocationLat = endLocationLat,
        endLocationLng = endLocationLng,
        notes = notes,
        createdAt = createdAt.toString(),
        updatedAt = updatedAt.toString()
    )
}

private fun Vehicle.toEntity(): VehicleEntity {
    return VehicleEntity(
        id = id,
        registrationNumber = registrationNumber,
        model = model,
        manufacturer = manufacturer,
        year = year,
        fuelType = fuelType,
        currentOdometer = currentOdometer,
        isAvailable = isAvailable
    )
}

private fun VehicleEntity.toDomainModel(): Vehicle {
    return Vehicle(
        id = id,
        registrationNumber = registrationNumber,
        model = model,
        manufacturer = manufacturer,
        year = year,
        fuelType = fuelType,
        currentOdometer = currentOdometer,
        isAvailable = isAvailable
    )
}