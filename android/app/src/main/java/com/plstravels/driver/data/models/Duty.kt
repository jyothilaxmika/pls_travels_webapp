package com.plstravels.driver.data.models

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.google.gson.annotations.SerializedName

/**
 * Duty data models for driver duty management
 */
@Entity(tableName = "duties")
data class Duty(
    @PrimaryKey
    val id: Int,
    val status: String,
    @SerializedName("start_time")
    val startTime: String?,
    @SerializedName("end_time")
    val endTime: String?,
    val vehicle: Vehicle? = null,
    val route: String?,
    @SerializedName("total_earnings")
    val totalEarnings: Double,
    @SerializedName("distance_km")
    val distanceKm: Double,
    @SerializedName("created_at")
    val createdAt: String?,
    
    // Local fields for offline management
    val isLocalOnly: Boolean = false,
    val syncStatus: String = "SYNCED", // SYNCED, PENDING, FAILED
    val localId: String? = null
)

@Entity(tableName = "vehicles")
data class Vehicle(
    @PrimaryKey
    val id: Int,
    @SerializedName("registration_number")
    val registrationNumber: String,
    val model: String,
    val manufacturer: String? = null,
    val year: Int? = null,
    @SerializedName("fuel_type")
    val fuelType: String? = null,
    @SerializedName("current_odometer")
    val currentOdometer: Double? = null,
    @SerializedName("is_available")
    val isAvailable: Boolean = true
)

/**
 * Duty management request/response models
 */
data class StartDutyRequest(
    @SerializedName("vehicle_id")
    val vehicleId: Int,
    @SerializedName("duty_type")
    val dutyType: String = "REGULAR",
    val route: String = "",
    @SerializedName("start_odometer")
    val startOdometer: Double = 0.0,
    @SerializedName("start_location")
    val startLocation: LocationData? = null
)

data class EndDutyRequest(
    @SerializedName("duty_id")
    val dutyId: Int? = null,
    @SerializedName("end_odometer")
    val endOdometer: Double = 0.0,
    @SerializedName("end_location")
    val endLocation: LocationData? = null,
    @SerializedName("total_revenue")
    val totalRevenue: Double = 0.0,
    val notes: String = ""
)

data class LocationData(
    val latitude: Double,
    val longitude: Double,
    val address: String? = null
)

data class DutyResponse(
    val success: Boolean,
    val message: String,
    val duty: DutyDetails? = null,
    val error: String? = null
)

data class DutyDetails(
    val id: Int,
    val status: String,
    @SerializedName("start_time")
    val startTime: String,
    @SerializedName("end_time")
    val endTime: String? = null,
    val vehicle: Vehicle,
    @SerializedName("distance_km")
    val distanceKm: Double = 0.0,
    @SerializedName("total_revenue")
    val totalRevenue: Double = 0.0,
    @SerializedName("duration_hours")
    val durationHours: Double = 0.0
)

data class DutiesResponse(
    val success: Boolean,
    val duties: List<Duty>,
    val pagination: PaginationInfo? = null,
    val error: String? = null
)

data class PaginationInfo(
    val page: Int,
    val pages: Int,
    @SerializedName("per_page")
    val perPage: Int,
    val total: Int,
    @SerializedName("has_next")
    val hasNext: Boolean,
    @SerializedName("has_prev")
    val hasPrev: Boolean
)

data class VehiclesResponse(
    val success: Boolean,
    val vehicles: List<Vehicle>,
    val error: String? = null
)