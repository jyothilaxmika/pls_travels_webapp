package com.plstravels.driver.data.model

import com.google.gson.annotations.SerializedName

/**
 * Duty data model for driver duty management
 */
data class Duty(
    @SerializedName("id")
    val id: Int,
    
    @SerializedName("driver_id")
    val driverId: Int,
    
    @SerializedName("vehicle_id")
    val vehicleId: Int?,
    
    @SerializedName("vehicle")
    val vehicle: Vehicle?,
    
    @SerializedName("duty_date")
    val dutyDate: String,
    
    @SerializedName("start_time")
    val startTime: String?,
    
    @SerializedName("end_time")
    val endTime: String?,
    
    @SerializedName("start_odometer")
    val startOdometer: Double?,
    
    @SerializedName("end_odometer")
    val endOdometer: Double?,
    
    @SerializedName("start_fuel_level")
    val startFuelLevel: Double?,
    
    @SerializedName("end_fuel_level")
    val endFuelLevel: Double?,
    
    @SerializedName("status")
    val status: String,
    
    @SerializedName("total_revenue")
    val totalRevenue: Double?,
    
    @SerializedName("total_trips")
    val totalTrips: Int?,
    
    @SerializedName("earnings")
    val earnings: Double?,
    
    @SerializedName("start_photo_url")
    val startPhotoUrl: String?,
    
    @SerializedName("end_photo_url")
    val endPhotoUrl: String?,
    
    @SerializedName("start_location_lat")
    val startLocationLat: Double?,
    
    @SerializedName("start_location_lng")
    val startLocationLng: Double?,
    
    @SerializedName("end_location_lat")
    val endLocationLat: Double?,
    
    @SerializedName("end_location_lng")
    val endLocationLng: Double?,
    
    @SerializedName("notes")
    val notes: String?,
    
    @SerializedName("created_at")
    val createdAt: String,
    
    @SerializedName("updated_at")
    val updatedAt: String
)

/**
 * Vehicle information for duty
 */
data class Vehicle(
    @SerializedName("id")
    val id: Int,
    
    @SerializedName("registration_number")
    val registrationNumber: String,
    
    @SerializedName("model")
    val model: String,
    
    @SerializedName("manufacturer")
    val manufacturer: String,
    
    @SerializedName("year")
    val year: Int?,
    
    @SerializedName("fuel_type")
    val fuelType: String,
    
    @SerializedName("current_odometer")
    val currentOdometer: Double,
    
    @SerializedName("is_available")
    val isAvailable: Boolean
)

/**
 * Duty start request
 */
data class DutyStartRequest(
    @SerializedName("vehicle_id")
    val vehicleId: Int,
    
    @SerializedName("start_odometer")
    val startOdometer: Double,
    
    @SerializedName("start_fuel_level")
    val startFuelLevel: Double,
    
    @SerializedName("latitude")
    val latitude: Double?,
    
    @SerializedName("longitude")
    val longitude: Double?,
    
    @SerializedName("photo_url")
    val photoUrl: String?,
    
    @SerializedName("notes")
    val notes: String?
)

/**
 * Duty end request
 */
data class DutyEndRequest(
    @SerializedName("duty_id")
    val dutyId: Int,
    
    @SerializedName("end_odometer")
    val endOdometer: Double,
    
    @SerializedName("end_fuel_level")
    val endFuelLevel: Double,
    
    @SerializedName("total_revenue")
    val totalRevenue: Double,
    
    @SerializedName("total_trips")
    val totalTrips: Int,
    
    @SerializedName("latitude")
    val latitude: Double?,
    
    @SerializedName("longitude")
    val longitude: Double?,
    
    @SerializedName("photo_url")
    val photoUrl: String?,
    
    @SerializedName("notes")
    val notes: String?
)

/**
 * API Response wrapper
 */
data class ApiResponse<T>(
    @SerializedName("success")
    val success: Boolean,
    
    @SerializedName("data")
    val data: T?,
    
    @SerializedName("message")
    val message: String?,
    
    @SerializedName("error")
    val error: String?
)