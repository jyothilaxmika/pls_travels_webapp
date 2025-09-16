package com.plstravels.driver.data.database.dao

import androidx.room.*
import com.plstravels.driver.data.database.entity.PhotoEntity

/**
 * Room DAO for photo operations
 */
@Dao
interface PhotoDao {
    
    @Query("SELECT * FROM photos WHERE id = :photoId")
    suspend fun getPhotoById(photoId: Long): PhotoEntity?
    
    @Query("SELECT * FROM photos WHERE dutyId = :dutyId")
    suspend fun getPhotosByDutyId(dutyId: Int): List<PhotoEntity>
    
    @Query("SELECT * FROM photos WHERE dutyId = :dutyId AND photoType = :photoType")
    suspend fun getPhotosByDutyIdAndType(dutyId: Int, photoType: String): List<PhotoEntity>
    
    @Query("SELECT * FROM photos WHERE photoType = :photoType")
    suspend fun getPhotosByType(photoType: String): List<PhotoEntity>
    
    @Query("SELECT * FROM photos WHERE isUploaded = 0")
    suspend fun getPendingUploads(): List<PhotoEntity>
    
    @Query("SELECT * FROM photos WHERE isUploaded = 0 AND uploadRetryCount < 3")
    suspend fun getRetryableUploads(): List<PhotoEntity>
    
    @Query("SELECT * FROM photos ORDER BY createdAt DESC")
    suspend fun getAllPhotos(): List<PhotoEntity>
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertPhoto(photo: PhotoEntity): Long
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertPhotos(photos: List<PhotoEntity>): List<Long>
    
    @Update
    suspend fun updatePhoto(photo: PhotoEntity)
    
    @Delete
    suspend fun deletePhoto(photo: PhotoEntity)
    
    @Query("DELETE FROM photos WHERE id = :photoId")
    suspend fun deletePhotoById(photoId: Long)
    
    @Query("DELETE FROM photos WHERE dutyId = :dutyId")
    suspend fun deletePhotosByDutyId(dutyId: Int)
    
    @Query("UPDATE photos SET isUploaded = :isUploaded, remoteUrl = :remoteUrl, uploadedAt = :uploadedAt WHERE id = :photoId")
    suspend fun updateUploadStatus(photoId: Long, isUploaded: Boolean, remoteUrl: String?, uploadedAt: Long?)
    
    @Query("UPDATE photos SET uploadRetryCount = uploadRetryCount + 1 WHERE id = :photoId")
    suspend fun incrementRetryCount(photoId: Long)
    
    @Query("UPDATE photos SET uploadRetryCount = 0 WHERE id = :photoId")
    suspend fun resetRetryCount(photoId: Long)
}