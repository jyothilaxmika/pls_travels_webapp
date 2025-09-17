package com.plstravels.driver.ui.duty

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.plstravels.driver.data.database.entity.DutyEntity
import com.plstravels.driver.data.database.entity.VehicleEntity
import com.plstravels.driver.data.model.*
import com.plstravels.driver.data.repository.DutyRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import timber.log.Timber
import java.time.LocalDateTime
import javax.inject.Inject

/**
 * ViewModel for duty management operations
 */
@HiltViewModel
class DutyViewModel @Inject constructor(
    private val dutyRepository: DutyRepository
) : ViewModel() {

    // UI State
    var uiState by mutableStateOf(DutyUiState())
        private set

    // Active duty from database (reactive)
    val activeDuty: StateFlow<DutyEntity?> = dutyRepository.getActiveDutyFlow()
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = null
        )

    // Recent duties
    val duties: StateFlow<List<DutyEntity>> = dutyRepository.getDutiesFlow()
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = emptyList()
        )

    // Available vehicles
    val availableVehicles: StateFlow<List<VehicleEntity>> = flow {
        val result = dutyRepository.getAvailableVehicles(forceRefresh = false)
        emit(result.getOrElse { emptyList() }.map { it.toEntity() })
    }.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = emptyList()
    )

    init {
        loadData()
    }

    /**
     * Load initial data
     */
    private fun loadData() {
        viewModelScope.launch {
            updateUiState(isLoading = true)
            try {
                // Load available vehicles
                dutyRepository.getAvailableVehicles(forceRefresh = true)
                updateUiState(isLoading = false)
            } catch (e: Exception) {
                Timber.e(e, "Failed to load initial data")
                updateUiState(isLoading = false, error = "Failed to load data")
            }
        }
    }

    /**
     * Start a new duty
     */
    fun startDuty(
        vehicleId: Int,
        startOdometer: Double,
        startFuelLevel: Double,
        photoUrl: String?,
        latitude: Double?,
        longitude: Double?,
        notes: String?
    ) {
        if (uiState.isLoading) return

        viewModelScope.launch {
            updateUiState(isLoading = true, error = null)
            
            try {
                val request = DutyStartRequest(
                    vehicleId = vehicleId,
                    startOdometer = startOdometer,
                    startFuelLevel = startFuelLevel,
                    photoUrl = photoUrl,
                    latitude = latitude,
                    longitude = longitude,
                    notes = notes
                )

                val result = dutyRepository.startDuty(request)
                result.fold(
                    onSuccess = { duty ->
                        updateUiState(
                            isLoading = false,
                            message = "Duty started successfully!",
                            dutyStarted = true
                        )
                        // Trigger refresh after successful operation
                        refreshData()
                    },
                    onFailure = { exception ->
                        updateUiState(
                            isLoading = false,
                            error = exception.message ?: "Failed to start duty"
                        )
                    }
                )
            } catch (e: Exception) {
                Timber.e(e, "Start duty error")
                updateUiState(
                    isLoading = false,
                    error = e.message ?: "Failed to start duty"
                )
            }
        }
    }

    /**
     * End active duty
     */
    fun endDuty(
        dutyId: Int,
        endOdometer: Double,
        endFuelLevel: Double,
        totalRevenue: Double?,
        totalTrips: Int?,
        photoUrl: String?,
        latitude: Double?,
        longitude: Double?,
        notes: String?
    ) {
        if (uiState.isLoading) return

        viewModelScope.launch {
            updateUiState(isLoading = true, error = null)
            
            try {
                val request = DutyEndRequest(
                    dutyId = dutyId,
                    endOdometer = endOdometer,
                    endFuelLevel = endFuelLevel,
                    totalRevenue = totalRevenue,
                    totalTrips = totalTrips,
                    photoUrl = photoUrl,
                    latitude = latitude,
                    longitude = longitude,
                    notes = notes
                )

                val result = dutyRepository.endDuty(request)
                result.fold(
                    onSuccess = { duty ->
                        updateUiState(
                            isLoading = false,
                            message = "Duty ended successfully!",
                            dutyEnded = true
                        )
                        // Trigger refresh after successful operation
                        refreshData()
                        // Sync offline duties if available
                        syncOfflineDuties()
                    },
                    onFailure = { exception ->
                        updateUiState(
                            isLoading = false,
                            error = exception.message ?: "Failed to end duty"
                        )
                    }
                )
            } catch (e: Exception) {
                Timber.e(e, "End duty error")
                updateUiState(
                    isLoading = false,
                    error = e.message ?: "Failed to end duty"
                )
            }
        }
    }

    /**
     * Refresh data from server
     */
    fun refreshData() {
        viewModelScope.launch {
            updateUiState(isRefreshing = true)
            try {
                dutyRepository.getAvailableVehicles(forceRefresh = true)
                dutyRepository.getDuties(forceRefresh = true)
                updateUiState(isRefreshing = false, message = "Data refreshed")
            } catch (e: Exception) {
                Timber.e(e, "Failed to refresh data")
                updateUiState(isRefreshing = false, error = "Failed to refresh data")
            }
        }
    }

    /**
     * Sync offline duties
     */
    fun syncOfflineDuties() {
        viewModelScope.launch {
            updateUiState(isSyncing = true)
            try {
                val result = dutyRepository.syncOfflineDuties()
                result.fold(
                    onSuccess = { syncedCount ->
                        val message = if (syncedCount > 0) {
                            "Synced $syncedCount offline duties"
                        } else {
                            "No offline duties to sync"
                        }
                        updateUiState(isSyncing = false, message = message)
                    },
                    onFailure = { exception ->
                        updateUiState(
                            isSyncing = false,
                            error = "Failed to sync offline duties: ${exception.message}"
                        )
                    }
                )
            } catch (e: Exception) {
                Timber.e(e, "Sync offline duties error")
                updateUiState(isSyncing = false, error = "Sync failed")
            }
        }
    }

    /**
     * Validate odometer reading
     */
    fun validateOdometer(currentReading: Double, vehicleCurrentOdometer: Double?): String? {
        if (currentReading <= 0) {
            return "Odometer reading must be greater than 0"
        }
        
        vehicleCurrentOdometer?.let { lastReading ->
            if (currentReading < lastReading) {
                return "Odometer reading cannot be less than previous reading ($lastReading km)"
            }
            
            val difference = currentReading - lastReading
            if (difference > 500) { // Reasonable daily limit
                return "Odometer reading seems too high. Difference: ${difference.toInt()} km"
            }
        }
        
        return null
    }

    /**
     * Validate fuel level
     */
    fun validateFuelLevel(fuelLevel: Double): String? {
        return when {
            fuelLevel < 0 -> "Fuel level cannot be negative"
            fuelLevel > 100 -> "Fuel level cannot exceed 100%"
            else -> null
        }
    }

    /**
     * Clear messages
     */
    fun clearMessage() {
        updateUiState(message = null)
    }

    /**
     * Clear errors
     */
    fun clearError() {
        updateUiState(error = null)
    }

    private fun updateUiState(
        isLoading: Boolean? = null,
        isRefreshing: Boolean? = null,
        isSyncing: Boolean? = null,
        dutyStarted: Boolean? = null,
        dutyEnded: Boolean? = null,
        error: String? = null,
        message: String? = null
    ) {
        uiState = uiState.copy(
            isLoading = isLoading ?: uiState.isLoading,
            isRefreshing = isRefreshing ?: uiState.isRefreshing,
            isSyncing = isSyncing ?: uiState.isSyncing,
            dutyStarted = dutyStarted ?: uiState.dutyStarted,
            dutyEnded = dutyEnded ?: uiState.dutyEnded,
            error = error,
            message = message
        )
    }
}

/**
 * UI state for duty management
 */
data class DutyUiState(
    val isLoading: Boolean = false,
    val isRefreshing: Boolean = false,
    val isSyncing: Boolean = false,
    val dutyStarted: Boolean = false,
    val dutyEnded: Boolean = false,
    val error: String? = null,
    val message: String? = null
)

// Extension function to convert Vehicle to VehicleEntity
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