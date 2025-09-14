package com.plstravels.driver.ui.notifications

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.plstravels.driver.data.models.Notification
import com.plstravels.driver.data.models.NotificationType
import com.plstravels.driver.data.repository.NotificationRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * ViewModel for notification management
 */
@HiltViewModel
class NotificationViewModel @Inject constructor(
    private val notificationRepository: NotificationRepository
) : ViewModel() {
    
    private val _uiState = MutableStateFlow(NotificationUiState())
    val uiState: StateFlow<NotificationUiState> = _uiState.asStateFlow()
    
    private val _currentFilter = MutableStateFlow("all")
    
    val notifications: StateFlow<List<Notification>> = _currentFilter
        .flatMapLatest { filter ->
            when (filter) {
                "unread" -> notificationRepository.getUnreadNotifications()
                "duty" -> notificationRepository.getNotificationsByType(NotificationType.DUTY_ASSIGNMENT)
                "dispatch" -> notificationRepository.getNotificationsByType(NotificationType.DISPATCH_MESSAGE)
                "emergency" -> notificationRepository.getNotificationsByType(NotificationType.EMERGENCY_ALERT)
                else -> notificationRepository.getAllNotifications()
            }
        }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = emptyList()
        )
    
    val unreadCount: StateFlow<Int> = notificationRepository.getUnreadNotifications()
        .map { it.size }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = 0
        )
    
    init {
        loadNotifications()
        initializeFCM()
        cleanupOldNotifications()
    }
    
    fun loadNotifications() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            
            try {
                // Notifications are loaded via StateFlow automatically
                _uiState.value = _uiState.value.copy(isLoading = false)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message ?: "Failed to load notifications"
                )
            }
        }
    }
    
    fun filterNotifications(filter: String) {
        _currentFilter.value = filter
    }
    
    fun markAsRead(notificationId: Long) {
        viewModelScope.launch {
            try {
                notificationRepository.markAsRead(notificationId)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    error = "Failed to mark notification as read"
                )
            }
        }
    }
    
    fun markAllAsRead() {
        viewModelScope.launch {
            try {
                notificationRepository.markAllAsRead()
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    error = "Failed to mark all notifications as read"
                )
            }
        }
    }
    
    fun deleteNotification(notificationId: Long) {
        viewModelScope.launch {
            try {
                notificationRepository.deleteNotification(notificationId)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    error = "Failed to delete notification"
                )
            }
        }
    }
    
    fun createTestNotification() {
        viewModelScope.launch {
            try {
                notificationRepository.createTestNotification()
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    error = "Failed to create test notification"
                )
            }
        }
    }
    
    private fun initializeFCM() {
        viewModelScope.launch {
            try {
                val result = notificationRepository.initializeFCM()
                if (result.isFailure) {
                    _uiState.value = _uiState.value.copy(
                        error = "Failed to initialize push notifications"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    error = "FCM initialization error: ${e.message}"
                )
            }
        }
    }
    
    private fun cleanupOldNotifications() {
        viewModelScope.launch {
            try {
                notificationRepository.cleanupOldNotifications()
            } catch (e: Exception) {
                // Silent cleanup failure
            }
        }
    }
    
    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}

/**
 * UI state for notification screen
 */
data class NotificationUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val selectedFilter: String = "all"
)