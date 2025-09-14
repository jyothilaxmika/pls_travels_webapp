package com.plstravels.driver.data.local

import androidx.room.TypeConverter
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.plstravels.driver.data.models.Vehicle
import com.plstravels.driver.data.models.PhotoType
import com.plstravels.driver.data.models.NotificationType
import com.plstravels.driver.data.models.NotificationPriority
import com.plstravels.driver.data.models.CommandType

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
    
    @TypeConverter
    fun fromPhotoType(photoType: PhotoType?): String? {
        return photoType?.name
    }
    
    @TypeConverter
    fun toPhotoType(photoTypeString: String?): PhotoType? {
        return photoTypeString?.let { PhotoType.valueOf(it) }
    }
    
    @TypeConverter
    fun fromNotificationType(notificationType: NotificationType?): String? {
        return notificationType?.name
    }
    
    @TypeConverter
    fun toNotificationType(notificationTypeString: String?): NotificationType? {
        return notificationTypeString?.let { NotificationType.valueOf(it) }
    }
    
    @TypeConverter
    fun fromNotificationPriority(priority: NotificationPriority?): String? {
        return priority?.name
    }
    
    @TypeConverter
    fun toNotificationPriority(priorityString: String?): NotificationPriority? {
        return priorityString?.let { NotificationPriority.valueOf(it) }
    }
    
    @TypeConverter
    fun fromCommandType(commandType: CommandType?): String? {
        return commandType?.name
    }
    
    @TypeConverter
    fun toCommandType(commandTypeString: String?): CommandType? {
        return commandTypeString?.let { CommandType.valueOf(it) }
    }
}