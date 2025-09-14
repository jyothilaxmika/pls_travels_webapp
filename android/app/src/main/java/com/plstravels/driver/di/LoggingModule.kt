package com.plstravels.driver.di

import android.content.Context
import com.plstravels.driver.utils.CrashReportingManager
import com.plstravels.driver.utils.LoggingConfig
import com.plstravels.driver.utils.ProdLogger
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

/**
 * Dependency injection module for logging and crash reporting components
 */
@Module
@InstallIn(SingletonComponent::class)
object LoggingModule {
    
    @Provides
    @Singleton
    fun provideCrashReportingManager(
        @ApplicationContext context: Context
    ): CrashReportingManager {
        return CrashReportingManager(context)
    }
    
    @Provides
    @Singleton
    fun provideLoggingConfig(
        crashReportingManager: CrashReportingManager
    ): LoggingConfig {
        return LoggingConfig(crashReportingManager)
    }
    
    @Provides
    @Singleton
    fun provideProdLogger(
        loggingConfig: LoggingConfig
    ): ProdLogger {
        return ProdLogger(loggingConfig)
    }
}