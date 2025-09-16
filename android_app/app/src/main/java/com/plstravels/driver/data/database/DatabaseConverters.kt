package com.plstravels.driver.data.database

import androidx.room.TypeConverter
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken

/**
 * Room database type converters
 */
class DatabaseConverters {

    private val gson = Gson()

    @TypeConverter
    fun fromStringMap(value: Map<String, String>?): String? {
        return if (value == null) null else gson.toJson(value)
    }

    @TypeConverter
    fun toStringMap(value: String?): Map<String, String>? {
        return if (value == null) null else {
            val type = object : TypeToken<Map<String, String>>() {}.type
            gson.fromJson(value, type)
        }
    }

    @TypeConverter
    fun fromStringList(value: List<String>?): String? {
        return if (value == null) null else gson.toJson(value)
    }

    @TypeConverter
    fun toStringList(value: String?): List<String>? {
        return if (value == null) null else {
            val type = object : TypeToken<List<String>>() {}.type
            gson.fromJson(value, type)
        }
    }
}