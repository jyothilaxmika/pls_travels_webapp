package com.plstravels.driver.camera

import android.content.Context
import android.util.Size
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import com.plstravels.driver.data.models.CameraCaptureConfig
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.CompletableDeferred
import java.io.File
import java.text.SimpleDateFormat
import java.util.*
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Manager for camera operations using CameraX
 * Handles camera lifecycle, capture, and configuration
 */
@Singleton
class CameraManager @Inject constructor(
    @ApplicationContext private val context: Context
) {
    
    private var cameraProvider: ProcessCameraProvider? = null
    private var imageCapture: ImageCapture? = null
    private var camera: Camera? = null
    private var currentConfig = CameraCaptureConfig()
    private var currentLensFacing: Int = CameraSelector.LENS_FACING_BACK
    
    companion object {
        private const val FILENAME_FORMAT = "yyyy-MM-dd-HH-mm-ss-SSS"
        private const val PHOTO_EXTENSION = ".jpg"
    }
    
    /**
     * Initialize camera with lifecycle and preview
     */
    suspend fun initializeCamera(
        lifecycleOwner: LifecycleOwner,
        previewView: PreviewView,
        config: CameraCaptureConfig = CameraCaptureConfig(),
        lensFacing: Int? = null
    ): Result<Unit> {
        return withContext(Dispatchers.Main) {
            try {
                currentConfig = config
                
                val cameraProviderFuture = ProcessCameraProvider.getInstance(context)
                cameraProvider = cameraProviderFuture.get()
                
                // Preview
                val preview = Preview.Builder()
                    .setTargetResolution(Size(config.targetResolution.width, config.targetResolution.height))
                    .build()
                
                preview.setSurfaceProvider(previewView.surfaceProvider)
                
                // Image capture use case
                imageCapture = ImageCapture.Builder()
                    .setTargetResolution(Size(config.targetResolution.width, config.targetResolution.height))
                    .setJpegQuality(config.jpegQuality)
                    .setFlashMode(if (config.enableFlash) ImageCapture.FLASH_MODE_ON else ImageCapture.FLASH_MODE_OFF)
                    .build()
                
                // Use provided lens facing or current state
                if (lensFacing != null) {
                    currentLensFacing = lensFacing
                }
                
                val cameraSelector = when (currentLensFacing) {
                    CameraSelector.LENS_FACING_FRONT -> CameraSelector.DEFAULT_FRONT_CAMERA
                    else -> CameraSelector.DEFAULT_BACK_CAMERA
                }
                
                // Unbind use cases before rebinding
                cameraProvider?.unbindAll()
                
                // Bind use cases to camera
                camera = cameraProvider?.bindToLifecycle(
                    lifecycleOwner,
                    cameraSelector,
                    preview,
                    imageCapture
                )
                
                Result.success(Unit)
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }
    
    /**
     * Capture photo and save to app's private directory
     */
    suspend fun capturePhoto(
        fileName: String? = null
    ): Result<File> {
        return withContext(Dispatchers.IO) {
            try {
                val imageCapture = imageCapture ?: return@withContext Result.failure(
                    IllegalStateException("Camera not initialized")
                )
                
                // Create output file
                val photoFile = createPhotoFile(fileName)
                
                // Create output options object which contains file + metadata
                val outputOptions = ImageCapture.OutputFileOptions.Builder(photoFile).build()
                
                // Set up capture listener, which is triggered after photo has been taken
                val result = CompletableDeferred<Result<File>>()
                
                imageCapture.takePicture(
                    outputOptions,
                    ContextCompat.getMainExecutor(context),
                    object : ImageCapture.OnImageSavedCallback {
                        override fun onError(exception: ImageCaptureException) {
                            result.complete(Result.failure(exception))
                        }
                        
                        override fun onImageSaved(output: ImageCapture.OutputFileResults) {
                            result.complete(Result.success(photoFile))
                        }
                    }
                )
                
                result.await()
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }
    
    /**
     * Toggle camera flash
     */
    fun toggleFlash(): Boolean {
        camera?.let { cam ->
            return if (cam.cameraInfo.hasFlashUnit()) {
                val currentFlashMode = imageCapture?.flashMode
                val newFlashMode = if (currentFlashMode == ImageCapture.FLASH_MODE_ON) {
                    ImageCapture.FLASH_MODE_OFF
                } else {
                    ImageCapture.FLASH_MODE_ON
                }
                imageCapture?.flashMode = newFlashMode
                newFlashMode == ImageCapture.FLASH_MODE_ON
            } else {
                false
            }
        }
        return false
    }
    
    /**
     * Check if camera has flash capability
     */
    fun hasFlash(): Boolean {
        return camera?.cameraInfo?.hasFlashUnit() ?: false
    }
    
    /**
     * Get current lens facing
     */
    fun getCurrentLensFacing(): Int {
        return currentLensFacing
    }
    
    /**
     * Check if currently using front camera
     */
    fun isFrontCamera(): Boolean {
        return currentLensFacing == CameraSelector.LENS_FACING_FRONT
    }
    
    /**
     * Check if currently using back camera
     */
    fun isBackCamera(): Boolean {
        return currentLensFacing == CameraSelector.LENS_FACING_BACK
    }
    
    /**
     * Switch between front and back camera
     */
    suspend fun switchCamera(
        lifecycleOwner: LifecycleOwner,
        previewView: PreviewView
    ): Result<Unit> {
        return withContext(Dispatchers.Main) {
            try {
                val cameraProvider = cameraProvider ?: return@withContext Result.failure(
                    IllegalStateException("Camera not initialized")
                )
                
                // Determine current camera and switch to the opposite
                val newLensFacing = if (currentLensFacing == CameraSelector.LENS_FACING_BACK) {
                    CameraSelector.LENS_FACING_FRONT
                } else {
                    CameraSelector.LENS_FACING_BACK
                }
                
                // Reinitialize with new camera
                initializeCamera(lifecycleOwner, previewView, currentConfig, newLensFacing)
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }
    
    /**
     * Release camera resources
     */
    fun release() {
        cameraProvider?.unbindAll()
        cameraProvider = null
        imageCapture = null
        camera = null
        // Reset to default back camera
        currentLensFacing = CameraSelector.LENS_FACING_BACK
    }
    
    private fun createPhotoFile(fileName: String?): File {
        val photosDir = File(context.getExternalFilesDir(null), "photos").apply {
            if (!exists()) mkdirs()
        }
        
        val name = fileName ?: SimpleDateFormat(FILENAME_FORMAT, Locale.getDefault())
            .format(System.currentTimeMillis())
        
        return File(photosDir, "$name$PHOTO_EXTENSION")
    }
    
    /**
     * Get photo storage directory
     */
    fun getPhotosDirectory(): File {
        return File(context.getExternalFilesDir(null), "photos").apply {
            if (!exists()) mkdirs()
        }
    }
    
    /**
     * Delete photo file from storage
     */
    fun deletePhotoFile(file: File): Boolean {
        return try {
            file.delete()
        } catch (e: Exception) {
            false
        }
    }
}