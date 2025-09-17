package com.plstravels.driver.utils

import android.content.Context
import android.net.Uri
import androidx.core.content.FileProvider
import timber.log.Timber
import java.io.File
import java.text.SimpleDateFormat
import java.util.*

/**
 * Helper class for photo capture operations
 */
class PhotoCaptureHelper(private val context: Context) {

    companion object {
        private const val PHOTOS_DIR = "Photos"
        private const val FILE_PROVIDER_AUTHORITY = "com.plstravels.driver.fileprovider"
        private val DATE_FORMAT = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault())
    }

    /**
     * Create a temporary image file for camera capture
     */
    fun createImageFile(prefix: String = "DUTY_"): Pair<File, Uri> {
        try {
            // Create an image file name
            val timeStamp = DATE_FORMAT.format(Date())
            val imageFileName = "${prefix}${timeStamp}_"
            
            // Get the Photos directory
            val photosDir = File(context.getExternalFilesDir(null), PHOTOS_DIR)
            if (!photosDir.exists()) {
                photosDir.mkdirs()
            }
            
            // Create the temporary file
            val imageFile = File.createTempFile(
                imageFileName,
                ".jpg",
                photosDir
            )
            
            // Create Uri using FileProvider
            val imageUri = FileProvider.getUriForFile(
                context,
                FILE_PROVIDER_AUTHORITY,
                imageFile
            )
            
            Timber.i("Created image file: ${imageFile.absolutePath}")
            return Pair(imageFile, imageUri)
            
        } catch (e: Exception) {
            Timber.e(e, "Error creating image file")
            throw e
        }
    }

    /**
     * Create a temporary image file specifically for duty start photos
     */
    fun createStartDutyImageFile(): Pair<File, Uri> {
        return createImageFile("START_DUTY_")
    }

    /**
     * Create a temporary image file specifically for duty end photos
     */
    fun createEndDutyImageFile(): Pair<File, Uri> {
        return createImageFile("END_DUTY_")
    }

    /**
     * Clean up old photo files (keep only last 50 files)
     */
    fun cleanupOldPhotos() {
        try {
            val photosDir = File(context.getExternalFilesDir(null), PHOTOS_DIR)
            if (photosDir.exists()) {
                val files = photosDir.listFiles { file ->
                    file.isFile && file.extension.lowercase() == "jpg"
                }
                
                if (files != null && files.size > 50) {
                    // Sort by last modified date (oldest first)
                    files.sortBy { it.lastModified() }
                    
                    // Delete oldest files
                    val filesToDelete = files.size - 50
                    for (i in 0 until filesToDelete) {
                        try {
                            files[i].delete()
                            Timber.d("Deleted old photo: ${files[i].name}")
                        } catch (e: Exception) {
                            Timber.w(e, "Failed to delete old photo: ${files[i].name}")
                        }
                    }
                }
            }
        } catch (e: Exception) {
            Timber.e(e, "Error cleaning up old photos")
        }
    }

    /**
     * Get the file path from Uri
     */
    fun getFilePathFromUri(uri: Uri): String? {
        return try {
            // For FileProvider URIs, get the path from the file
            val file = File(uri.path ?: return null)
            file.absolutePath
        } catch (e: Exception) {
            Timber.e(e, "Error getting file path from Uri")
            null
        }
    }

    /**
     * Check if file exists and is readable
     */
    fun isValidImageFile(filePath: String?): Boolean {
        if (filePath.isNullOrBlank()) return false
        
        val file = File(filePath)
        return file.exists() && file.canRead() && file.length() > 0
    }

    /**
     * Get photo file size in MB
     */
    fun getFileSizeInMB(filePath: String): Double {
        val file = File(filePath)
        return if (file.exists()) {
            file.length() / (1024.0 * 1024.0)
        } else {
            0.0
        }
    }
}