package com.plstravels.driver.di

import android.content.Context
import com.plstravels.driver.data.storage.SecureStorageManager
import com.plstravels.driver.security.SecureBiometricManager
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

/**
 * Dependency injection module for security components
 */
@Module
@InstallIn(SingletonComponent::class)
object SecurityModule {
    
    @Provides
    @Singleton
    fun provideSecureStorageManager(
        @ApplicationContext context: Context
    ): SecureStorageManager {
        return SecureStorageManager(context)
    }
    
    @Provides
    @Singleton
    fun provideSecureBiometricManager(
        @ApplicationContext context: Context
    ): SecureBiometricManager {
        return SecureBiometricManager(context)
    }
}