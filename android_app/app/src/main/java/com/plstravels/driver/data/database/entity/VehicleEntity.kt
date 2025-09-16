package com.plstravels.driver.data.database.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Room entity for vehicle data
 */
@Entity(tableName = "vehicles")
data class VehicleEntity(
    @PrimaryKey
    val id: Int,
    val registrationNumber: String,
    val model: String,
    val manufacturer: String,
    val year: Int?,
    val fuelType: String,
    val currentOdometer: Double,
    val isAvailable: Boolean,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis()
)