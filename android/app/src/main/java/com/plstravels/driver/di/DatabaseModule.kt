package com.plstravels.driver.di

import android.content.Context
import androidx.room.Room
import com.plstravels.driver.data.local.*
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

/**
 * Hilt module for Room database dependencies
 */
@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {
    
    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): PLSDatabase {
        return Room.databaseBuilder(
            context,
            PLSDatabase::class.java,
            PLSDatabase.DATABASE_NAME
        )
        .fallbackToDestructiveMigration() // For development - remove in production
        .build()
    }
    
    @Provides
    fun provideUserDao(database: PLSDatabase): UserDao = database.userDao()
    
    @Provides
    fun provideDutyDao(database: PLSDatabase): DutyDao = database.dutyDao()
    
    @Provides
    fun provideVehicleDao(database: PLSDatabase): VehicleDao = database.vehicleDao()
    
    @Provides
    fun provideLocationDao(database: PLSDatabase): LocationDao = database.locationDao()
    
    @Provides
    fun providePhotoDao(database: PLSDatabase): PhotoDao = database.photoDao()
    
    @Provides
    fun provideNotificationDao(database: PLSDatabase): NotificationDao = database.notificationDao()
}