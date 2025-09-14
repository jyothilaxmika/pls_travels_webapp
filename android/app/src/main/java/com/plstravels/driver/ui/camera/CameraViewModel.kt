package com.plstravels.driver.ui.camera

import androidx.camera.view.PreviewView
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.plstravels.driver.camera.CameraManager
import com.plstravels.driver.data.models.PhotoType
import com.plstravels.driver.data.repository.PhotoRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * ViewModel for camera operations and photo capture
 */
@HiltViewModel
class CameraViewModel @Inject constructor(
    private val cameraManager: CameraManager,
    private val photoRepository: PhotoRepository
) : ViewModel() {
    
    private val _uiState = MutableStateFlow(CameraUiState())
    val uiState: StateFlow<CameraUiState> = _uiState.asStateFlow()
    
    fun initializeCamera(lifecycleOwner: LifecycleOwner, previewView: PreviewView) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isInitializing = true, error = null)
            
            try {
                val result = cameraManager.initializeCamera(lifecycleOwner, previewView)
                
                if (result.isSuccess) {
                    _uiState.value = _uiState.value.copy(
                        isInitializing = false,
                        isCameraReady = true,
                        hasFlash = cameraManager.hasFlash()
                    )
                } else {
                    _uiState.value = _uiState.value.copy(
                        isInitializing = false,
                        isCameraReady = false,
                        error = result.exceptionOrNull()?.message ?: "Failed to initialize camera"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isInitializing = false,
                    isCameraReady = false,
                    error = e.message ?: "Camera initialization error"
                )
            }
        }
    }
    
    fun capturePhoto(photoType: PhotoType, dutyId: Int?) {
        if (!_uiState.value.isCameraReady || _uiState.value.isCapturing) return
        
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isCapturing = true, error = null)
            
            try {
                val result = photoRepository.capturePhoto(
                    photoType = photoType,
                    dutyId = dutyId,
                    description = "Captured via ${photoType.displayName}"
                )
                
                if (result.isSuccess) {
                    val photo = result.getOrNull()!!
                    _uiState.value = _uiState.value.copy(
                        isCapturing = false,
                        capturedPhotoPath = photo.localFilePath,
                        lastCapturedPhoto = photo
                    )
                } else {
                    _uiState.value = _uiState.value.copy(
                        isCapturing = false,
                        error = result.exceptionOrNull()?.message ?: "Failed to capture photo"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isCapturing = false,
                    error = e.message ?: "Photo capture error"
                )
            }
        }
    }
    
    fun toggleFlash() {
        if (!_uiState.value.isCameraReady || !_uiState.value.hasFlash) return
        
        val isFlashOn = cameraManager.toggleFlash()
        _uiState.value = _uiState.value.copy(isFlashOn = isFlashOn)
    }
    
    fun switchCamera(lifecycleOwner: LifecycleOwner, previewView: PreviewView) {
        if (!_uiState.value.isCameraReady || _uiState.value.isCapturing) return
        
        viewModelScope.launch {
            try {
                val result = cameraManager.switchCamera(lifecycleOwner, previewView)
                
                if (result.isFailure) {
                    _uiState.value = _uiState.value.copy(
                        error = "Failed to switch camera"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    error = e.message ?: "Camera switch error"
                )
            }
        }
    }
    
    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
    
    fun resetCaptureState() {
        _uiState.value = _uiState.value.copy(
            capturedPhotoPath = null,
            lastCapturedPhoto = null
        )
    }
    
    override fun onCleared() {
        super.onCleared()
        cameraManager.release()
    }
}

/**
 * UI state for camera screen
 */
data class CameraUiState(
    val isInitializing: Boolean = false,
    val isCameraReady: Boolean = false,
    val isCapturing: Boolean = false,
    val hasFlash: Boolean = false,
    val isFlashOn: Boolean = false,
    val capturedPhotoPath: String? = null,
    val lastCapturedPhoto: com.plstravels.driver.data.models.Photo? = null,
    val error: String? = null
)