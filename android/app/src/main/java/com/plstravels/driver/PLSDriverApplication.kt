package com.plstravels.driver

import android.app.Application
import android.util.Log
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import com.plstravels.driver.workers.LocationSyncWorker
import com.plstravels.driver.service.SyncManager
import com.plstravels.driver.service.BackgroundSyncInitializer
import com.plstravels.driver.utils.CrashReportingManager
import com.plstravels.driver.utils.LoggingConfig
import com.plstravels.driver.utils.ProdLogger
import com.plstravels.driver.utils.MemoryManager
import com.plstravels.driver.utils.PerformanceMonitor
import com.plstravels.driver.utils.DatabasePerformanceOptimizer
import com.plstravels.driver.utils.ImageOptimizer
import com.plstravels.driver.utils.UIPerformanceOptimizer
import com.plstravels.driver.utils.LocationTrackingOptimizer
import dagger.hilt.android.HiltAndroidApp
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import java.util.UUID
import javax.inject.Inject

/**
 * Main application class for PLS Driver app
 * Handles app-wide initialization including WorkManager and background sync system
 */
@HiltAndroidApp
class PLSDriverApplication : Application(), Configuration.Provider {
    
    @Inject
    lateinit var workerFactory: HiltWorkerFactory
    
    @Inject
    lateinit var syncManager: SyncManager
    
    @Inject
    lateinit var backgroundSyncInitializer: BackgroundSyncInitializer
    
    @Inject
    lateinit var crashReportingManager: CrashReportingManager
    
    @Inject
    lateinit var loggingConfig: LoggingConfig
    
    @Inject
    lateinit var logger: ProdLogger
    
    @Inject
    lateinit var memoryManager: MemoryManager
    
    @Inject
    lateinit var performanceMonitor: PerformanceMonitor
    
    @Inject
    lateinit var databaseOptimizer: DatabasePerformanceOptimizer
    
    @Inject
    lateinit var imageOptimizer: ImageOptimizer
    
    @Inject
    lateinit var uiPerformanceOptimizer: UIPerformanceOptimizer
    
    @Inject
    lateinit var locationTrackingOptimizer: LocationTrackingOptimizer
    
    private val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private val sessionId = UUID.randomUUID().toString()
    
    companion object {
        private const val TAG = "PLSDriverApplication"
    }
    
    override fun getWorkManagerConfiguration() =
        Configuration.Builder()
            .setWorkerFactory(workerFactory)
            .build()
            
    override fun onCreate() {
        super.onCreate()
        
        Log.i(TAG, "🚀 PLS Driver Application starting...")
        
        // Initialize crash reporting and enhanced logging system FIRST
        applicationScope.launch {
            try {
                initializeCrashReportingAndLogging()
                logger.i(TAG, "✅ Crash reporting and logging system initialized")
            } catch (e: Exception) {
                Log.e(TAG, "❌ Failed to initialize crash reporting and logging", e)
                // Continue with basic logging if enhanced logging fails
            }
        }
        
        // Initialize performance optimization components
        applicationScope.launch {
            try {
                initializePerformanceOptimizations()
                logger.i(TAG, "✅ Performance optimization system initialized")
            } catch (e: Exception) {
                logger.e(TAG, "❌ Failed to initialize performance optimizations", throwable = e)
                crashReportingManager.recordCustomException(
                    "Performance optimization initialization failed", 
                    e,
                    mapOf("component" to "performance_optimization", "phase" to "initialization")
                )
                // App should continue to work even if performance optimizations fail
            }
        }
        
        // Initialize sync manager for offline-first data synchronization
        try {
            syncManager.initialize()
            logger.i(TAG, "✅ Sync manager initialized")
        } catch (e: Exception) {
            logger.e(TAG, "❌ Failed to initialize sync manager", throwable = e)
        }
        
        // Initialize location sync worker
        try {
            LocationSyncWorker.schedulePeriodicSync(this)
            logger.i(TAG, "✅ Location sync worker scheduled")
        } catch (e: Exception) {
            logger.e(TAG, "❌ Failed to schedule location sync worker", throwable = e)
        }
        
        // Initialize background sync system
        applicationScope.launch {
            try {
                backgroundSyncInitializer.initialize(this@PLSDriverApplication)
                logger.i(TAG, "✅ Background sync initialization complete")
            } catch (e: Exception) {
                logger.e(TAG, "❌ Failed to initialize background sync", throwable = e)
                crashReportingManager.recordCustomException(
                    "Background sync initialization failed", 
                    e,
                    mapOf("component" to "background_sync", "phase" to "initialization")
                )
                // App should continue to work even if background sync fails
            }
        }
        
        logger.i(TAG, "✅ PLS Driver Application started successfully", 
            mapOf("session_id" to sessionId))
    }
    
    /**
     * Initialize crash reporting and enhanced logging system
     */
    private suspend fun initializeCrashReportingAndLogging() {
        try {
            // Initialize crash reporting manager first
            crashReportingManager.initialize()
            crashReportingManager.setSessionId(sessionId)
            crashReportingManager.setAppState("starting")
            
            // Initialize logging configuration
            loggingConfig.initialize()
            
            // Set initial app context for crash reporting
            crashReportingManager.setCustomKey("initialization_time", System.currentTimeMillis().toString())
            
        } catch (e: Exception) {
            Log.e(TAG, "Critical error during crash reporting initialization", e)
            throw e
        }
    }
    
    /**
     * Initialize performance optimization components
     */
    private suspend fun initializePerformanceOptimizations() {
        try {
            // Initialize memory manager first (other components depend on it)
            memoryManager.initialize()
            logger.i(TAG, "✅ Memory manager initialized")
            
            // Initialize performance monitor (for tracking all performance metrics)
            performanceMonitor.initialize()
            logger.i(TAG, "✅ Performance monitor initialized")
            
            // Initialize database optimizer
            databaseOptimizer.initialize()
            logger.i(TAG, "✅ Database optimizer initialized")
            
            // Initialize image optimizer
            imageOptimizer.initialize()
            logger.i(TAG, "✅ Image optimizer initialized")
            
            // Initialize UI performance optimizer
            uiPerformanceOptimizer.initialize()
            logger.i(TAG, "✅ UI performance optimizer initialized")
            
            // Initialize location tracking optimizer
            locationTrackingOptimizer.initialize()
            logger.i(TAG, "✅ Location tracking optimizer initialized")
            
            // Log performance initialization metrics
            val memoryInfo = memoryManager.getCurrentMemoryInfo()
            logger.i(TAG, "Performance optimization initialization complete", mapOf(
                "memory_usage_mb" to (memoryInfo.usedHeap / 1024 / 1024).toString(),
                "memory_percentage" to String.format("%.1f", memoryInfo.usedPercentage * 100),
                "optimization_level" to memoryInfo.level.name,
                "session_id" to sessionId
            ))
            
        } catch (e: Exception) {
            Log.e(TAG, "Critical error during performance optimization initialization", e)
            throw e
        }
    }
    
    override fun onTerminate() {
        super.onTerminate()
        logger.i(TAG, "PLS Driver Application terminating...")
        crashReportingManager.setAppState("terminating")
        
        try {
            // Shutdown performance optimization components first
            shutdownPerformanceOptimizations()
            logger.i(TAG, "Performance optimization shutdown complete")
        } catch (e: Exception) {
            logger.e(TAG, "Error during performance optimization shutdown", throwable = e)
            crashReportingManager.recordCustomException(
                "Performance optimization shutdown failed", 
                e,
                mapOf("component" to "performance_optimization", "phase" to "shutdown")
            )
        }
        
        try {
            backgroundSyncInitializer.shutdown(this)
            logger.i(TAG, "Background sync shutdown complete")
        } catch (e: Exception) {
            logger.e(TAG, "Error during background sync shutdown", throwable = e)
            crashReportingManager.recordCustomException(
                "Background sync shutdown failed", 
                e,
                mapOf("component" to "background_sync", "phase" to "shutdown")
            )
        }
    }
    
    /**
     * Shutdown performance optimization components
     */
    private fun shutdownPerformanceOptimizations() {
        try {
            // Shutdown in reverse order of initialization
            locationTrackingOptimizer.shutdown()
            uiPerformanceOptimizer.shutdown()
            imageOptimizer.shutdown()
            databaseOptimizer.shutdown()
            performanceMonitor.shutdown()
            memoryManager.shutdown()
            
            logger.i(TAG, "All performance optimization components shut down successfully")
        } catch (e: Exception) {
            logger.e(TAG, "Error during performance optimization shutdown", throwable = e)
        }
    }
    
    override fun onLowMemory() {
        super.onLowMemory()
        logger.w(TAG, "⚠️ Low memory warning - triggering memory optimization")
        
        // Use the new MemoryManager for handling low memory conditions
        try {
            val memoryInfo = memoryManager.getCurrentMemoryInfo()
            memoryManager.requestGarbageCollection(force = true)
            
            logger.w(TAG, "Memory optimization triggered", mapOf(
                "memory_level" to memoryInfo.level.name,
                "used_percentage" to String.format("%.1f", memoryInfo.usedPercentage * 100),
                "used_heap_mb" to (memoryInfo.usedHeap / 1024 / 1024).toString()
            ))
        } catch (e: Exception) {
            logger.e(TAG, "Error during low memory handling", throwable = e)
        }
        
        crashReportingManager.setCustomKey("memory_status", "low")
        crashReportingManager.recordCustomException(
            "Low memory condition detected",
            additionalData = mapOf(
                "memory_event" to "onLowMemory",
                "timestamp" to System.currentTimeMillis().toString()
            )
        )
    }
    
    override fun onTrimMemory(level: Int) {
        super.onTrimMemory(level)
        
        val memoryLevel = when (level) {
            TRIM_MEMORY_RUNNING_LOW -> {
                logger.w(TAG, "Memory trimming: RUNNING_LOW")
                "running_low"
            }
            TRIM_MEMORY_RUNNING_CRITICAL -> {
                logger.w(TAG, "Memory trimming: RUNNING_CRITICAL")
                "running_critical"
            }
            TRIM_MEMORY_UI_HIDDEN -> {
                logger.i(TAG, "UI hidden - app backgrounded, background sync should continue")
                crashReportingManager.setAppState("background")
                "ui_hidden"
            }
            TRIM_MEMORY_BACKGROUND -> {
                logger.i(TAG, "App in background - background sync active")
                "background"
            }
            TRIM_MEMORY_MODERATE -> {
                logger.w(TAG, "Memory pressure: MODERATE")
                "moderate"
            }
            TRIM_MEMORY_COMPLETE -> {
                logger.w(TAG, "Memory pressure: COMPLETE - app may be killed soon")
                "complete"
            }
            else -> "unknown_$level"
        }
        
        crashReportingManager.setCustomKey("memory_trim_level", memoryLevel)
        
        // Report critical memory conditions
        if (level == TRIM_MEMORY_COMPLETE || level == TRIM_MEMORY_RUNNING_CRITICAL) {
            crashReportingManager.recordCustomException(
                "Critical memory pressure detected",
                additionalData = mapOf(
                    "memory_level" to memoryLevel,
                    "trim_level" to level.toString(),
                    "session_id" to sessionId
                )
            )
        }
    }
}