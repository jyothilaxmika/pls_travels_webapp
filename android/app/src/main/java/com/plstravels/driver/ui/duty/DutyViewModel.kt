package com.plstravels.driver.ui.duty

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.plstravels.driver.data.models.Duty
import com.plstravels.driver.data.models.Vehicle
import com.plstravels.driver.data.models.LocationData
import com.plstravels.driver.data.repository.DutyRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * ViewModel for duty management
 */
@HiltViewModel
class DutyViewModel @Inject constructor(
    private val dutyRepository: DutyRepository
) : ViewModel() {
    
    private val _uiState = MutableStateFlow(DutyUiState())
    val uiState: StateFlow<DutyUiState> = _uiState.asStateFlow()
    
    private val _duties = MutableStateFlow<List<Duty>>(emptyList())
    val duties: StateFlow<List<Duty>> = _duties.asStateFlow()
    
    private val _vehicles = MutableStateFlow<List<Vehicle>>(emptyList())
    val vehicles: StateFlow<List<Vehicle>> = _vehicles.asStateFlow()
    
    private val _activeDuty = MutableStateFlow<Duty?>(null)
    val activeDuty: StateFlow<Duty?> = _activeDuty.asStateFlow()
    
    init {
        loadInitialData()
    }
    
    private fun loadInitialData() {
        viewModelScope.launch {
            // Combine multiple data streams
            combine(
                dutyRepository.getAllDuties(),
                dutyRepository.getActiveDuty(),
                dutyRepository.getAvailableVehicles()
            ) { duties, activeDuty, vehicles ->
                _duties.value = duties
                _activeDuty.value = activeDuty
                _vehicles.value = vehicles
            }
        }
        
        // Load fresh data from server
        refreshData()
    }
    
    fun refreshData() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            
            try {
                // Load duties and vehicles from server
                dutyRepository.refreshDuties()
                dutyRepository.refreshVehicles()
                
                _uiState.value = _uiState.value.copy(isLoading = false)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message ?: "Failed to refresh data"
                )
            }
        }
    }
    
    fun startDuty(
        vehicleId: Int,
        startOdometer: Double,
        currentLocation: LocationData?
    ) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            
            try {
                val result = dutyRepository.startDuty(vehicleId, startOdometer, currentLocation)
                
                if (result.isSuccess) {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        message = "Duty started successfully"
                    )
                    refreshData() // Refresh to get updated active duty
                } else {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = result.exceptionOrNull()?.message ?: "Failed to start duty"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message ?: "Network error occurred"
                )
            }
        }
    }
    
    fun endDuty(
        dutyId: Int?,
        endOdometer: Double,
        totalRevenue: Double,
        currentLocation: LocationData?,
        notes: String = ""
    ) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            
            try {
                val result = dutyRepository.endDuty(
                    dutyId, endOdometer, totalRevenue, currentLocation, notes
                )
                
                if (result.isSuccess) {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        message = "Duty ended successfully"
                    )
                    refreshData() // Refresh to get updated duties
                } else {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = result.exceptionOrNull()?.message ?: "Failed to end duty"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message ?: "Network error occurred"
                )
            }
        }
    }
    
    fun clearMessage() {
        _uiState.value = _uiState.value.copy(message = null)
    }
    
    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}

/**
 * UI state for duty management
 */
data class DutyUiState(
    val isLoading: Boolean = false,
    val message: String? = null,
    val error: String? = null,
    val selectedVehicle: Vehicle? = null
)