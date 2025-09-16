package com.plstravels.driver.ui.navigation

import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.plstravels.driver.data.repository.AuthRepository
import com.plstravels.driver.ui.auth.LoginScreen
import com.plstravels.driver.ui.auth.AuthViewModel
import com.plstravels.driver.ui.dashboard.DashboardScreen
import com.plstravels.driver.ui.splash.SplashScreen
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking

/**
 * Main navigation component for the app
 */
@Composable
fun PLSNavigation(
    navController: NavHostController,
    modifier: Modifier = Modifier,
    authRepository: AuthRepository = hiltViewModel<AuthViewModel>().authRepository
) {
    // Check authentication status
    val isLoggedIn by authRepository.isLoggedIn.collectAsState(initial = false)
    
    NavHost(
        navController = navController,
        startDestination = PLSDestinations.SPLASH,
        modifier = modifier
    ) {
        // Splash Screen
        composable(PLSDestinations.SPLASH) {
            SplashScreen(
                onNavigateToLogin = {
                    navController.navigate(PLSDestinations.LOGIN) {
                        popUpTo(PLSDestinations.SPLASH) { inclusive = true }
                    }
                },
                onNavigateToDashboard = {
                    navController.navigate(PLSDestinations.DASHBOARD) {
                        popUpTo(PLSDestinations.SPLASH) { inclusive = true }
                    }
                },
                isLoggedIn = isLoggedIn
            )
        }
        
        // Authentication Flow
        composable(PLSDestinations.LOGIN) {
            val authViewModel: AuthViewModel = hiltViewModel()
            LoginScreen(
                viewModel = authViewModel,
                onLoginSuccess = {
                    navController.navigate(PLSDestinations.DASHBOARD) {
                        popUpTo(PLSDestinations.LOGIN) { inclusive = true }
                    }
                }
            )
        }
        
        // Main Dashboard
        composable(PLSDestinations.DASHBOARD) {
            DashboardScreen(
                onLogout = {
                    navController.navigate(PLSDestinations.LOGIN) {
                        popUpTo(PLSDestinations.DASHBOARD) { inclusive = true }
                    }
                }
            )
        }
    }
}

/**
 * Navigation destinations
 */
object PLSDestinations {
    const val SPLASH = "splash"
    const val LOGIN = "login"
    const val DASHBOARD = "dashboard"
    const val DUTY_MANAGEMENT = "duty_management"
    const val CAMERA = "camera"
    const val PROFILE = "profile"
    const val ADVANCE_PAYMENTS = "advance_payments"
    const val SETTINGS = "settings"
}