package com.plstravels.driver.data.local

import androidx.room.TypeConverter
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.plstravels.driver.data.models.Vehicle

/**
 * Room type converters for complex data types
 */
class Converters {
    
    private val gson = Gson()
    
    @TypeConverter
    fun fromVehicle(vehicle: Vehicle?): String? {
        return if (vehicle == null) null else gson.toJson(vehicle)
    }
    
    @TypeConverter
    fun toVehicle(vehicleString: String?): Vehicle? {
        return if (vehicleString == null) null else {
            val type = object : TypeToken<Vehicle>() {}.type
            gson.fromJson(vehicleString, type)
        }
    }
}