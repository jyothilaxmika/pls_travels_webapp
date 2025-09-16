package com.plstravels.driver.service

import android.app.Service
import android.content.Intent
import android.os.IBinder
import timber.log.Timber

/**
 * Background service for syncing data with server
 */
class BackgroundSyncService : Service() {
    
    override fun onBind(intent: Intent?): IBinder? = null
    
    override fun onCreate() {
        super.onCreate()
        Timber.d("BackgroundSyncService created")
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_SYNC_DATA -> syncData()
            ACTION_SYNC_PHOTOS -> syncPhotos()
            ACTION_SYNC_LOCATIONS -> syncLocations()
        }
        return START_NOT_STICKY
    }
    
    private fun syncData() {
        Timber.d("Starting data sync")
        
        // TODO: Implement data sync logic
        // syncDuties()
        // syncUserProfile()
        // syncAdvancePayments()
        
        stopSelf()
    }
    
    private fun syncPhotos() {
        Timber.d("Starting photo sync")
        
        // TODO: Implement photo sync logic
        // uploadPendingPhotos()
        
        stopSelf()
    }
    
    private fun syncLocations() {
        Timber.d("Starting location sync")
        
        // TODO: Implement location sync logic
        // uploadPendingLocations()
        
        stopSelf()
    }
    
    companion object {
        const val ACTION_SYNC_DATA = "SYNC_DATA"
        const val ACTION_SYNC_PHOTOS = "SYNC_PHOTOS"
        const val ACTION_SYNC_LOCATIONS = "SYNC_LOCATIONS"
    }
}