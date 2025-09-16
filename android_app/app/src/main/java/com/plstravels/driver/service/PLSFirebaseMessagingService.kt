package com.plstravels.driver.service

import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import timber.log.Timber
import javax.inject.Inject

/**
 * Firebase Cloud Messaging service for push notifications
 */
class PLSFirebaseMessagingService : FirebaseMessagingService() {
    
    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Timber.d("New FCM token received: $token")
        
        // TODO: Send token to server
        // sendTokenToServer(token)
    }
    
    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        super.onMessageReceived(remoteMessage)
        
        Timber.d("FCM message received from: ${remoteMessage.from}")
        
        // Handle notification payload
        remoteMessage.notification?.let { notification ->
            Timber.d("Notification title: ${notification.title}")
            Timber.d("Notification body: ${notification.body}")
            
            // TODO: Show notification to user
            // showNotification(notification.title, notification.body)
        }
        
        // Handle data payload
        if (remoteMessage.data.isNotEmpty()) {
            Timber.d("FCM data payload: ${remoteMessage.data}")
            
            // TODO: Handle data-only messages
            // handleDataMessage(remoteMessage.data)
        }
    }
}