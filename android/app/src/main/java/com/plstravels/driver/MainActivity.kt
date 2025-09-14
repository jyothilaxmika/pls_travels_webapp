package com.plstravels.driver

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.core.app.ActivityCompat
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.plstravels.driver.ui.auth.AuthScreen
import com.plstravels.driver.ui.auth.AuthViewModel
import com.plstravels.driver.ui.duty.DutyScreen
import com.plstravels.driver.ui.camera.CameraScreen
import com.plstravels.driver.ui.notifications.NotificationScreen
import com.plstravels.driver.ui.sync.SyncStatusScreen
import com.plstravels.driver.ui.theme.PLSDriverTheme
import com.plstravels.driver.data.models.PhotoType
import com.plstravels.driver.data.repository.NotificationRepository
import com.plstravels.driver.utils.NotificationPermissionHelper
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    
    private val authViewModel: AuthViewModel by viewModels()
    
    @Inject
    lateinit var notificationRepository: NotificationRepository
    
    private val activityScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    
    companion object {
        private const val NOTIFICATION_PERMISSION_REQUEST_CODE = 1003
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Initialize FCM and request notification permissions
        initializeNotifications()
        
        setContent {
            PLSDriverTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    PLSDriverApp(authViewModel)
                }
            }
        }
    }
    
    private fun initializeNotifications() {
        // Request notification permission for Android 13+
        if (NotificationPermissionHelper.shouldRequestNotificationPermission(this)) {
            ActivityCompat.requestPermissions(
                this,
                NotificationPermissionHelper.getRequiredPermissions(),
                NOTIFICATION_PERMISSION_REQUEST_CODE
            )
        } else {
            // Permission already granted or not required, initialize FCM
            initializeFCM()
        }
    }
    
    private fun initializeFCM() {
        activityScope.launch {
            try {
                notificationRepository.initializeFCM()
                // Optionally subscribe to default topics
                notificationRepository.subscribeToTopics(listOf("driver_updates", "system_alerts"))
            } catch (e: Exception) {
                // FCM initialization failed, but app can still function
            }
        }
    }
    
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        
        when (requestCode) {
            NOTIFICATION_PERMISSION_REQUEST_CODE -> {
                // Always initialize FCM regardless of permission result
                // FCM will still work for high-priority notifications even if permission is denied
                initializeFCM()
            }
        }
    }
}

@Composable
fun PLSDriverApp(authViewModel: AuthViewModel) {
    val navController = rememberNavController()
    val isLoggedIn by authViewModel.isLoggedIn.collectAsState()
    
    NavHost(
        navController = navController,
        startDestination = if (isLoggedIn) "duty" else "auth"
    ) {
        composable("auth") {
            AuthScreen(
                authViewModel = authViewModel,
                onLoginSuccess = {
                    navController.navigate("duty") {
                        popUpTo("auth") { inclusive = true }
                    }
                }
            )
        }
        
        composable("duty") {
            DutyScreen(
                onLogout = {
                    navController.navigate("auth") {
                        popUpTo("duty") { inclusive = true }
                    }
                },
                onNavigateToCamera = { photoType, dutyId ->
                    navController.navigate("camera/${photoType.name}/${dutyId ?: -1}")
                },
                onNavigateToNotifications = {
                    navController.navigate("notifications")
                },
                onNavigateToSync = {
                    navController.navigate("sync_status")
                }
            )
        }
        
        composable("notifications") {
            NotificationScreen(
                onBack = {
                    navController.popBackStack()
                }
            )
        }
        
        composable("sync_status") {
            SyncStatusScreen(
                onBack = {
                    navController.popBackStack()
                }
            )
        }
        
        composable("camera/{photoType}/{dutyId}") { backStackEntry ->
            val photoTypeName = backStackEntry.arguments?.getString("photoType") ?: ""
            val dutyId = backStackEntry.arguments?.getString("dutyId")?.toIntOrNull()
            
            val photoType = try {
                PhotoType.valueOf(photoTypeName)
            } catch (e: Exception) {
                PhotoType.GENERAL
            }
            
            CameraScreen(
                photoType = photoType,
                dutyId = if (dutyId == -1) null else dutyId,
                onPhotoCapture = { photoPath ->
                    navController.popBackStack()
                },
                onCancel = {
                    navController.popBackStack()
                }
            )
        }
    }
}