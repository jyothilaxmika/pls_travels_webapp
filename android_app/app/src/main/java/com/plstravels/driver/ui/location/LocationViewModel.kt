package com.plstravels.driver.ui.location

import androidx.compose.runtime.*
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.plstravels.driver.data.repository.LocationRepository
import com.plstravels.driver.data.repository.LocationStats
import com.plstravels.driver.utils.LocationPermissionHelper
import com.plstravels.driver.utils.LocationPermissionState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import timber.log.Timber
import javax.inject.Inject

/**
 * ViewModel for location-related functionality
 */
@HiltViewModel
class LocationViewModel @Inject constructor(
    private val locationRepository: LocationRepository
) : ViewModel() {

    // UI State
    var uiState by mutableStateOf(LocationUiState())
        private set

    // Location statistics flow
    val locationStats: StateFlow<LocationStats> = locationRepository.getLocationStats()
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = LocationStats()
        )

    /**
     * Sync unsynced locations with server
     */
    fun syncLocations() {
        viewModelScope.launch {
            try {
                updateUiState(isSyncing = true)
                
                val result = locationRepository.syncUnsyncedLocations()
                result.fold(
                    onSuccess = { syncedCount ->
                        updateUiState(
                            isSyncing = false,
                            message = if (syncedCount > 0) {
                                "Synced $syncedCount locations successfully"
                            } else {
                                "No locations to sync"
                            }
                        )
                    },
                    onFailure = { exception ->
                        updateUiState(
                            isSyncing = false,
                            error = "Failed to sync locations: ${exception.message}"
                        )
                    }
                )
                
            } catch (e: Exception) {
                Timber.e(e, "Error syncing locations")
                updateUiState(
                    isSyncing = false,
                    error = "Sync failed"
                )
            }
        }
    }

    /**
     * Clean up old locations
     */
    fun cleanupOldLocations() {
        viewModelScope.launch {
            try {
                updateUiState(isCleaningUp = true)
                
                val result = locationRepository.cleanupOldLocations()
                result.fold(
                    onSuccess = { cleanedCount ->
                        updateUiState(
                            isCleaningUp = false,
                            message = if (cleanedCount > 0) {
                                "Cleaned up $cleanedCount old locations"
                            } else {
                                "No old locations to clean up"
                            }
                        )
                    },
                    onFailure = { exception ->
                        updateUiState(
                            isCleaningUp = false,
                            error = "Failed to cleanup: ${exception.message}"
                        )
                    }
                )
                
            } catch (e: Exception) {
                Timber.e(e, "Error cleaning up locations")
                updateUiState(
                    isCleaningUp = false,
                    error = "Cleanup failed"
                )
            }
        }
    }

    /**
     * Get recent locations for display
     */
    fun getRecentLocations(): StateFlow<List<com.plstravels.driver.data.database.entity.LocationEntity>> {
        return flow {
            try {
                val locations = locationRepository.getRecentLocations(20)
                emit(locations)
            } catch (e: Exception) {
                Timber.e(e, "Failed to get recent locations")
                emit(emptyList())
            }
        }.stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = emptyList()
        )
    }

    /**
     * Clear all messages
     */
    fun clearMessages() {
        updateUiState(message = null, error = null)
    }

    /**
     * Update UI state helper
     */
    private fun updateUiState(
        isSyncing: Boolean = uiState.isSyncing,
        isCleaningUp: Boolean = uiState.isCleaningUp,
        message: String? = uiState.message,
        error: String? = uiState.error
    ) {
        uiState = uiState.copy(
            isSyncing = isSyncing,
            isCleaningUp = isCleaningUp,
            message = message,
            error = error
        )
    }
}

/**
 * UI state for location screen
 */
data class LocationUiState(
    val isSyncing: Boolean = false,
    val isCleaningUp: Boolean = false,
    val message: String? = null,
    val error: String? = null
)