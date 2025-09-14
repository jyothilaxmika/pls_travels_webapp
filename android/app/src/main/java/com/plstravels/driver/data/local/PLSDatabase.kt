package com.plstravels.driver.data.local

import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverters
import android.content.Context
import com.plstravels.driver.data.models.Duty
import com.plstravels.driver.data.models.User
import com.plstravels.driver.data.models.Vehicle
import com.plstravels.driver.data.models.LocationPoint
import com.plstravels.driver.data.models.LocationSession

/**
 * Room database for offline storage and caching
 */
@Database(
    entities = [User::class, Duty::class, Vehicle::class, LocationPoint::class, LocationSession::class],
    version = 2,
    exportSchema = false
)
@TypeConverters(Converters::class)
abstract class PLSDatabase : RoomDatabase() {
    
    abstract fun userDao(): UserDao
    abstract fun dutyDao(): DutyDao
    abstract fun vehicleDao(): VehicleDao
    abstract fun locationDao(): LocationDao
    
    companion object {
        const val DATABASE_NAME = "pls_driver_database"
    }
}