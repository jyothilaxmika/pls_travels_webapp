package com.plstravels.driver

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
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.plstravels.driver.ui.auth.AuthScreen
import com.plstravels.driver.ui.auth.AuthViewModel
import com.plstravels.driver.ui.duty.DutyScreen
import com.plstravels.driver.ui.camera.CameraScreen
import com.plstravels.driver.ui.theme.PLSDriverTheme
import com.plstravels.driver.data.models.PhotoType
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    
    private val authViewModel: AuthViewModel by viewModels()
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
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