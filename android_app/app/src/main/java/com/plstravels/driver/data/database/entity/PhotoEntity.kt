package com.plstravels.driver.data.database.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Room entity for photo data
 */
@Entity(tableName = "photos")
data class PhotoEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val dutyId: Int?,
    val localFilePath: String,
    val remoteUrl: String?,
    val photoType: String, // "START_DUTY", "END_DUTY", "DOCUMENT"
    val mimeType: String,
    val fileSize: Long,
    val isUploaded: Boolean = false,
    val uploadRetryCount: Int = 0,
    val createdAt: Long = System.currentTimeMillis(),
    val uploadedAt: Long? = null
)