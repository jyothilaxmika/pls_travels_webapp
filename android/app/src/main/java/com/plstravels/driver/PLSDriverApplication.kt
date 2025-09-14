package com.plstravels.driver

import android.app.Application
import android.util.Log
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import com.plstravels.driver.workers.LocationSyncWorker
import com.plstravels.driver.service.SyncManager
import com.plstravels.driver.service.BackgroundSyncInitializer
import dagger.hilt.android.HiltAndroidApp
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
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
    
    private val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    
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
        
        // Initialize sync manager for offline-first data synchronization
        syncManager.initialize()
        
        // Initialize location sync worker
        LocationSyncWorker.schedulePeriodicSync(this)
        
        // Initialize background sync system
        applicationScope.launch {
            try {
                backgroundSyncInitializer.initialize(this@PLSDriverApplication)
                Log.i(TAG, "✅ Background sync initialization complete")
            } catch (e: Exception) {
                Log.e(TAG, "❌ Failed to initialize background sync", e)
                // App should continue to work even if background sync fails
            }
        }
        
        Log.i(TAG, "✅ PLS Driver Application started successfully")
    }
    
    override fun onTerminate() {
        super.onTerminate()
        Log.i(TAG, "PLS Driver Application terminating...")
        
        try {
            backgroundSyncInitializer.shutdown(this)
            Log.i(TAG, "Background sync shutdown complete")
        } catch (e: Exception) {
            Log.e(TAG, "Error during background sync shutdown", e)
        }
    }
    
    override fun onLowMemory() {
        super.onLowMemory()
        Log.w(TAG, "⚠️ Low memory warning - background sync may be throttled")
    }
    
    override fun onTrimMemory(level: Int) {
        super.onTrimMemory(level)
        
        when (level) {
            TRIM_MEMORY_RUNNING_LOW -> {
                Log.w(TAG, "Memory trimming: RUNNING_LOW")
            }
            TRIM_MEMORY_RUNNING_CRITICAL -> {
                Log.w(TAG, "Memory trimming: RUNNING_CRITICAL")
            }
            TRIM_MEMORY_UI_HIDDEN -> {
                Log.i(TAG, "UI hidden - app backgrounded, background sync should continue")
            }
            TRIM_MEMORY_BACKGROUND -> {
                Log.i(TAG, "App in background - background sync active")
            }
            TRIM_MEMORY_MODERATE -> {
                Log.w(TAG, "Memory pressure: MODERATE")
            }
            TRIM_MEMORY_COMPLETE -> {
                Log.w(TAG, "Memory pressure: COMPLETE - app may be killed soon")
            }
        }
    }
}