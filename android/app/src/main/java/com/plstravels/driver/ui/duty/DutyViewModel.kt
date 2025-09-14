package com.plstravels.driver.ui.duty

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.plstravels.driver.data.models.Duty
import com.plstravels.driver.data.models.Vehicle
import com.plstravels.driver.data.models.LocationData
import com.plstravels.driver.data.repository.DutyRepository
import com.plstravels.driver.data.repository.LocationRepository
import com.plstravels.driver.data.repository.PhotoRepository
import com.plstravels.driver.data.repository.ConnectivityRepository
import com.plstravels.driver.data.repository.CommandQueueRepository
import com.plstravels.driver.service.LocationTrackingService
import com.plstravels.driver.utils.LocationPermissionHelper
import com.plstravels.driver.workers.LocationSyncWorker
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.launch
import android.content.Context
import android.content.Intent
import javax.inject.Inject

/**
 * ViewModel for duty management
 */
@HiltViewModel
class DutyViewModel @Inject constructor(
    private val dutyRepository: DutyRepository,
    private val locationRepository: LocationRepository,
    private val photoRepository: PhotoRepository,
    private val connectivityRepository: ConnectivityRepository,
    private val commandQueueRepository: CommandQueueRepository,
    @ApplicationContext private val context: Context
) : ViewModel() {
    
    private val _uiState = MutableStateFlow(DutyUiState())
    val uiState: StateFlow<DutyUiState> = _uiState.asStateFlow()
    
    private val _duties = MutableStateFlow<List<Duty>>(emptyList())
    val duties: StateFlow<List<Duty>> = _duties.asStateFlow()
    
    private val _vehicles = MutableStateFlow<List<Vehicle>>(emptyList())
    val vehicles: StateFlow<List<Vehicle>> = _vehicles.asStateFlow()
    
    private val _activeDuty = MutableStateFlow<Duty?>(null)
    val activeDuty: StateFlow<Duty?> = _activeDuty.asStateFlow()
    
    private val _locationPermissionsGranted = MutableStateFlow(false)
    val locationPermissionsGranted: StateFlow<Boolean> = _locationPermissionsGranted.asStateFlow()
    
    private val _showLocationPermissionDialog = MutableStateFlow(false)
    val showLocationPermissionDialog: StateFlow<Boolean> = _showLocationPermissionDialog.asStateFlow()
    
    private val _showPhotoCaptureSheet = MutableStateFlow(false)
    val showPhotoCaptureSheet: StateFlow<Boolean> = _showPhotoCaptureSheet.asStateFlow()
    
    private val _currentDutyPhotos = MutableStateFlow<List<com.plstravels.driver.data.models.Photo>>(emptyList())
    val currentDutyPhotos: StateFlow<List<com.plstravels.driver.data.models.Photo>> = _currentDutyPhotos.asStateFlow()
    
    // Connectivity and sync status flows
    val connectivityStatus = combine(
        connectivityRepository.isConnected,
        connectivityRepository.networkType
    ) { isConnected, networkType ->
        ConnectivityStatus(isConnected, networkType)
    }.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = ConnectivityStatus(false, ConnectivityRepository.NetworkType.NONE)
    )
    
    val syncStatus = commandQueueRepository.getPendingCommandCount().combine(
        connectivityRepository.isConnected
    ) { pendingCount, isConnected ->
        SyncStatus(
            pendingCount = pendingCount,
            isSyncing = false, // This would be managed by SyncManager in a real implementation
            lastSyncTime = null,
            isConnected = isConnected
        )
    }.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = SyncStatus(0, false, null, false)
    )
    
    init {
        loadInitialData()
        checkLocationPermissions()
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
                    // Start location tracking if permissions are granted
                    val dutyDetails = result.getOrNull()
                    if (dutyDetails != null && _locationPermissionsGranted.value) {
                        startLocationTracking(dutyDetails.id)
                    }
                    
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
                    // Stop location tracking
                    stopLocationTracking()
                    
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
    
    private fun checkLocationPermissions() {
        _locationPermissionsGranted.value = LocationPermissionHelper.hasAllRequiredPermissions(context)
    }
    
    fun requestLocationPermissions() {
        if (!LocationPermissionHelper.hasAllRequiredPermissions(context)) {
            _showLocationPermissionDialog.value = true
        } else {
            _locationPermissionsGranted.value = true
        }
    }
    
    fun onLocationPermissionsGranted() {
        _locationPermissionsGranted.value = true
        _showLocationPermissionDialog.value = false
        
        // Start location sync worker
        LocationSyncWorker.schedulePeriodicSync(context)
    }
    
    fun onLocationPermissionsDenied() {
        _locationPermissionsGranted.value = false
        _showLocationPermissionDialog.value = false
    }
    
    fun dismissLocationPermissionDialog() {
        _showLocationPermissionDialog.value = false
    }
    
    private fun startLocationTracking(dutyId: Int) {
        viewModelScope.launch {
            try {
                // Start location session in repository
                locationRepository.startLocationSession(dutyId)
                
                // Start foreground location service
                val intent = Intent(context, LocationTrackingService::class.java).apply {
                    action = LocationTrackingService.ACTION_START_TRACKING
                    putExtra(LocationTrackingService.EXTRA_DUTY_ID, dutyId)
                }
                context.startForegroundService(intent)
                
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    error = "Failed to start location tracking: ${e.message}"
                )
            }
        }
    }
    
    private fun stopLocationTracking() {
        viewModelScope.launch {
            try {
                // Stop foreground location service
                val intent = Intent(context, LocationTrackingService::class.java).apply {
                    action = LocationTrackingService.ACTION_STOP_TRACKING
                }
                context.startService(intent)
                
                // Trigger immediate sync of pending locations
                LocationSyncWorker.scheduleImmediateSync(context)
                
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    error = "Failed to stop location tracking: ${e.message}"
                )
            }
        }
    }
    
    fun showPhotoCaptureSheet() {
        _showPhotoCaptureSheet.value = true
    }
    
    fun dismissPhotoCaptureSheet() {
        _showPhotoCaptureSheet.value = false
    }
    
    fun loadPhotosForDuty(dutyId: Int) {
        viewModelScope.launch {
            photoRepository.getPhotosForDuty(dutyId).collect { photos ->
                _currentDutyPhotos.value = photos
            }
        }
    }
    
    fun getRequiredPhotosForDutyStart(): List<com.plstravels.driver.data.models.PhotoType> {
        return photoRepository.getRequiredDutyStartPhotos()
    }
    
    fun getRequiredPhotosForDutyEnd(): List<com.plstravels.driver.data.models.PhotoType> {
        return photoRepository.getRequiredDutyEndPhotos()
    }
}

/**
 * Data class for connectivity status
 */
data class ConnectivityStatus(
    val isConnected: Boolean,
    val networkType: ConnectivityRepository.NetworkType
)

/**
 * Data class for sync status  
 */
data class SyncStatus(
    val pendingCount: Int,
    val isSyncing: Boolean,
    val lastSyncTime: Long?,
    val isConnected: Boolean
)

/**
 * UI state for duty management
 */
data class DutyUiState(
    val isLoading: Boolean = false,
    val message: String? = null,
    val error: String? = null,
    val selectedVehicle: Vehicle? = null
)