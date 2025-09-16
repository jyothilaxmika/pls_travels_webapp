package com.plstravels.driver.data.database

import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverters
import android.content.Context
import com.plstravels.driver.data.database.dao.*
import com.plstravels.driver.data.database.entity.*

/**
 * Room database for offline data storage
 */
@Database(
    entities = [
        UserEntity::class,
        DutyEntity::class,
        VehicleEntity::class,
        LocationEntity::class,
        PhotoEntity::class,
        AdvancePaymentEntity::class
    ],
    version = 1,
    exportSchema = false
)
@TypeConverters(DatabaseConverters::class)
abstract class AppDatabase : RoomDatabase() {

    abstract fun userDao(): UserDao
    abstract fun dutyDao(): DutyDao
    abstract fun vehicleDao(): VehicleDao
    abstract fun locationDao(): LocationDao
    abstract fun photoDao(): PhotoDao
    abstract fun advancePaymentDao(): AdvancePaymentDao

    companion object {
        const val DATABASE_NAME = "pls_travels_driver.db"

        fun create(context: Context): AppDatabase {
            return Room.databaseBuilder(
                context,
                AppDatabase::class.java,
                DATABASE_NAME
            )
                .fallbackToDestructiveMigration()
                .build()
        }
    }
}