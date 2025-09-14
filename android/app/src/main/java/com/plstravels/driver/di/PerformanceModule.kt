package com.plstravels.driver.di

import android.content.Context
import com.plstravels.driver.data.local.PLSDatabase
import com.plstravels.driver.utils.*
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

/**
 * Dependency injection module for performance optimization components
 */
@Module
@InstallIn(SingletonComponent::class)
object PerformanceModule {
    
    @Provides
    @Singleton
    fun provideMemoryManager(
        @ApplicationContext context: Context,
        logger: ProdLogger
    ): MemoryManager {
        return MemoryManager(context, logger)
    }
    
    @Provides
    @Singleton
    fun provideDatabasePerformanceOptimizer(
        database: PLSDatabase,
        logger: ProdLogger
    ): DatabasePerformanceOptimizer {
        return DatabasePerformanceOptimizer(database, logger)
    }
    
    @Provides
    @Singleton
    fun providePerformanceMonitor(
        @ApplicationContext context: Context,
        logger: ProdLogger,
        memoryManager: MemoryManager
    ): PerformanceMonitor {
        return PerformanceMonitor(context, logger, memoryManager)
    }
    
    @Provides
    @Singleton
    fun provideImageOptimizer(
        @ApplicationContext context: Context,
        logger: ProdLogger,
        memoryManager: MemoryManager
    ): ImageOptimizer {
        return ImageOptimizer(context, logger, memoryManager)
    }
    
    @Provides
    @Singleton
    fun provideUIPerformanceOptimizer(
        logger: ProdLogger,
        memoryManager: MemoryManager
    ): UIPerformanceOptimizer {
        return UIPerformanceOptimizer(logger, memoryManager)
    }
    
    @Provides
    @Singleton
    fun provideLocationTrackingOptimizer(
        @ApplicationContext context: Context,
        logger: ProdLogger,
        memoryManager: MemoryManager
    ): LocationTrackingOptimizer {
        return LocationTrackingOptimizer(context, logger, memoryManager)
    }
}