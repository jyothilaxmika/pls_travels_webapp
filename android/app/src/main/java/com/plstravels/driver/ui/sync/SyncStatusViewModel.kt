package com.plstravels.driver.ui.sync

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.plstravels.driver.data.repository.CommandQueueRepository
import com.plstravels.driver.data.repository.ConnectivityRepository
import com.plstravels.driver.service.SyncManager
import com.plstravels.driver.data.models.CommandType
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * ViewModel for sync status screen
 */
@HiltViewModel
class SyncStatusViewModel @Inject constructor(
    private val commandQueueRepository: CommandQueueRepository,
    private val connectivityRepository: ConnectivityRepository,
    private val syncManager: SyncManager
) : ViewModel() {
    
    private val _uiState = MutableStateFlow(SyncScreenUiState())
    val uiState: StateFlow<SyncScreenUiState> = _uiState.asStateFlow()
    
    val syncStatus = combine(
        connectivityRepository.isConnected,
        connectivityRepository.networkType,
        commandQueueRepository.getPendingCommandCount(),
        _uiState
    ) { isConnected, networkType, pendingCount, state ->
        SyncStatusUiState(
            isConnected = isConnected,
            networkType = networkType,
            pendingCount = pendingCount,
            isSyncing = state.isSyncing,
            lastSyncTime = state.lastSyncTime,
            isMetered = connectivityRepository.isMeteredConnection()
        )
    }.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = SyncStatusUiState()
    )
    
    val pendingCommands = commandQueueRepository.getAllCommands()
        .map { commands ->
            commands.map { command ->
                PendingCommandUiState(
                    id = command.id,
                    type = command.type,
                    typeDisplayName = getCommandDisplayName(command.type),
                    timestamp = command.timestamp,
                    retryCount = command.retryCount,
                    maxRetries = command.maxRetries,
                    lastError = command.lastError,
                    isExecuting = command.isExecuting
                )
            }
        }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = emptyList()
        )
    
    fun refreshData() {
        viewModelScope.launch {
            try {
                _uiState.value = _uiState.value.copy(isLoading = true)
                
                val status = syncManager.getSyncStatus()
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    lastSyncTime = status.lastSyncAttempt
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message
                )
            }
        }
    }
    
    fun forceSync() {
        viewModelScope.launch {
            try {
                _uiState.value = _uiState.value.copy(isSyncing = true)
                
                val syncedCount = syncManager.triggerSync()
                
                _uiState.value = _uiState.value.copy(
                    isSyncing = false,
                    lastSyncTime = System.currentTimeMillis()
                )
                
                // Optionally show success message
                if (syncedCount > 0) {
                    _uiState.value = _uiState.value.copy(
                        message = "Synced $syncedCount operations"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isSyncing = false,
                    error = e.message
                )
            }
        }
    }
    
    private fun getCommandDisplayName(type: CommandType): String {
        return when (type) {
            CommandType.START_DUTY -> "Start Duty"
            CommandType.END_DUTY -> "End Duty"
            CommandType.UPDATE_LOCATION -> "Location Update"
            CommandType.UPLOAD_PHOTO -> "Photo Upload"
            CommandType.UPDATE_FCM_TOKEN -> "Update Notifications"
            CommandType.ACCEPT_DUTY_ASSIGNMENT -> "Accept Duty Assignment"
        }
    }
}

/**
 * UI state for the sync status screen
 */
data class SyncScreenUiState(
    val isLoading: Boolean = false,
    val isSyncing: Boolean = false,
    val lastSyncTime: Long? = null,
    val error: String? = null,
    val message: String? = null
)

/**
 * UI state for sync status overview
 */
data class SyncStatusUiState(
    val isConnected: Boolean = false,
    val networkType: ConnectivityRepository.NetworkType = ConnectivityRepository.NetworkType.NONE,
    val pendingCount: Int = 0,
    val isSyncing: Boolean = false,
    val lastSyncTime: Long? = null,
    val isMetered: Boolean = false
)

/**
 * UI state for individual pending commands
 */
data class PendingCommandUiState(
    val id: String,
    val type: CommandType,
    val typeDisplayName: String,
    val timestamp: Long,
    val retryCount: Int,
    val maxRetries: Int,
    val lastError: String?,
    val isExecuting: Boolean
)