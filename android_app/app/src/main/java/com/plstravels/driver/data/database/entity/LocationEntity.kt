package com.plstravels.driver.data.database.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Room entity for location tracking data
 */
@Entity(tableName = "locations")
data class LocationEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val driverId: Int,
    val latitude: Double,
    val longitude: Double,
    val accuracy: Float,
    val speed: Float,
    val heading: Float,
    val timestamp: Long,
    val isSynced: Boolean = false,
    val createdAt: Long = System.currentTimeMillis()
)