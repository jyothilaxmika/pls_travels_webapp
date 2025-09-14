package com.plstravels.driver.data.local

import androidx.room.*
import com.plstravels.driver.data.models.Photo
import com.plstravels.driver.data.models.PhotoType
import kotlinx.coroutines.flow.Flow

/**
 * Room DAO for photo management
 */
@Dao
interface PhotoDao {
    
    @Query("SELECT * FROM photos ORDER BY timestamp DESC")
    fun getAllPhotos(): Flow<List<Photo>>
    
    @Query("SELECT * FROM photos WHERE dutyId = :dutyId ORDER BY timestamp DESC")
    fun getPhotosForDuty(dutyId: Int): Flow<List<Photo>>
    
    @Query("SELECT * FROM photos WHERE photoType = :photoType ORDER BY timestamp DESC")
    fun getPhotosByType(photoType: PhotoType): Flow<List<Photo>>
    
    @Query("SELECT * FROM photos WHERE isUploaded = 0 ORDER BY timestamp ASC LIMIT :limit")
    suspend fun getPendingUploadPhotos(limit: Int = 20): List<Photo>
    
    @Query("SELECT COUNT(*) FROM photos WHERE isUploaded = 0")
    suspend fun getPendingUploadCount(): Int
    
    @Query("SELECT * FROM photos WHERE id = :photoId")
    suspend fun getPhotoById(photoId: Long): Photo?
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertPhoto(photo: Photo): Long
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertPhotos(photos: List<Photo>)
    
    @Update
    suspend fun updatePhoto(photo: Photo)
    
    @Query("UPDATE photos SET isUploaded = 1, serverUrl = :serverUrl WHERE id = :photoId")
    suspend fun markPhotoAsUploaded(photoId: Long, serverUrl: String)
    
    @Query("UPDATE photos SET uploadRetryCount = uploadRetryCount + 1, uploadError = :error WHERE id = :photoId")
    suspend fun incrementUploadRetryCount(photoId: Long, error: String?)
    
    @Delete
    suspend fun deletePhoto(photo: Photo)
    
    @Query("DELETE FROM photos WHERE isUploaded = 1 AND timestamp < :cutoffTime")
    suspend fun deleteOldUploadedPhotos(cutoffTime: Long)
    
    @Query("DELETE FROM photos WHERE dutyId = :dutyId")
    suspend fun deletePhotosForDuty(dutyId: Int)
    
    // Statistics queries
    @Query("SELECT COUNT(*) FROM photos WHERE dutyId = :dutyId")
    suspend fun getPhotoCountForDuty(dutyId: Int): Int
    
    @Query("SELECT COUNT(*) FROM photos WHERE photoType = :photoType AND timestamp >= :startTime")
    suspend fun getPhotoCountByTypeAndDate(photoType: PhotoType, startTime: Long): Int
}