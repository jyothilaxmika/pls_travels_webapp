package com.plstravels.driver

import android.app.Application
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import com.plstravels.driver.workers.LocationSyncWorker
import com.plstravels.driver.service.SyncManager
import dagger.hilt.android.HiltAndroidApp
import javax.inject.Inject

@HiltAndroidApp
class PLSDriverApplication : Application(), Configuration.Provider {
    
    @Inject
    lateinit var workerFactory: HiltWorkerFactory
    
    @Inject
    lateinit var syncManager: SyncManager
    
    override fun getWorkManagerConfiguration() =
        Configuration.Builder()
            .setWorkerFactory(workerFactory)
            .build()
            
    override fun onCreate() {
        super.onCreate()
        
        // Initialize sync manager for offline-first data synchronization
        syncManager.initialize()
        
        // Initialize location sync worker
        LocationSyncWorker.schedulePeriodicSync(this)
    }
}