package com.plstravels.driver.ui

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.lifecycleScope
import androidx.navigation.compose.rememberNavController
import com.plstravels.driver.data.repository.AuthRepository
import com.plstravels.driver.ui.navigation.PLSNavigation
import com.plstravels.driver.ui.theme.PLSTravelsTheme
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import timber.log.Timber
import javax.inject.Inject

/**
 * Main Activity for PLS Travels Driver App
 * Entry point with Jetpack Compose UI
 */
@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject
    lateinit var authRepository: AuthRepository

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        Timber.i("MainActivity started")
        
        enableEdgeToEdge()
        
        // Sync FCM token on app start if user is logged in
        syncFcmTokenOnAppStart()
        
        setContent {
            PLSTravelsTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    PLSDriverApp()
                }
            }
        }
    }

    /**
     * Sync FCM token with server when app starts (if user is already logged in)
     * This ensures the server has the latest FCM token even if it changed while the app was closed
     */
    private fun syncFcmTokenOnAppStart() {
        lifecycleScope.launch {
            try {
                // Check if user is logged in
                val isLoggedIn = authRepository.isLoggedIn.first()
                
                if (isLoggedIn) {
                    Timber.d("User is logged in, syncing FCM token on app start")
                    
                    authRepository.syncCurrentFcmToken().fold(
                        onSuccess = {
                            Timber.i("FCM token synced successfully on app start")
                        },
                        onFailure = { exception ->
                            Timber.w(exception, "Failed to sync FCM token on app start (non-critical)")
                        }
                    )
                } else {
                    Timber.d("User not logged in, skipping FCM token sync")
                }
            } catch (e: Exception) {
                Timber.w(e, "Exception during FCM token sync on app start (non-critical)")
            }
        }
    }
}

@Composable
fun PLSDriverApp() {
    val navController = rememberNavController()
    
    Scaffold(
        modifier = Modifier.fillMaxSize()
    ) { innerPadding ->
        PLSNavigation(
            navController = navController,
            modifier = Modifier.padding(innerPadding)
        )
    }
}