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
import androidx.navigation.compose.rememberNavController
import com.plstravels.driver.ui.navigation.PLSNavigation
import com.plstravels.driver.ui.theme.PLSTravelsTheme
import dagger.hilt.android.AndroidEntryPoint
import timber.log.Timber

/**
 * Main Activity for PLS Travels Driver App
 * Entry point with Jetpack Compose UI
 */
@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        Timber.i("MainActivity started")
        
        enableEdgeToEdge()
        
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