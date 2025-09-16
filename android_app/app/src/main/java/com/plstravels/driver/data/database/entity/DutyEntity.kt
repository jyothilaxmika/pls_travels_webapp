package com.plstravels.driver.data.database.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Room entity for duty data
 */
@Entity(tableName = "duties")
data class DutyEntity(
    @PrimaryKey
    val id: Int,
    val driverId: Int,
    val vehicleId: Int?,
    val dutyDate: String,
    val startTime: String?,
    val endTime: String?,
    val startOdometer: Double?,
    val endOdometer: Double?,
    val startFuelLevel: Double?,
    val endFuelLevel: Double?,
    val status: String,
    val totalRevenue: Double?,
    val totalTrips: Int?,
    val earnings: Double?,
    val startPhotoUrl: String?,
    val endPhotoUrl: String?,
    val startLocationLat: Double?,
    val startLocationLng: Double?,
    val endLocationLat: Double?,
    val endLocationLng: Double?,
    val notes: String?,
    val isSynced: Boolean = false,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis()
)