package com.plstravels.driver.ui.auth

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.platform.LocalContext
import androidx.fragment.app.FragmentActivity

/**
 * Login screen with OTP authentication
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LoginScreen(
    viewModel: AuthViewModel,
    onLoginSuccess: () -> Unit,
    modifier: Modifier = Modifier
) {
    val uiState = viewModel.uiState
    val context = LocalContext.current
    val isBiometricEnabled by viewModel.authRepository.isBiometricEnabled.collectAsState(initial = false)
    
    // Navigate on successful login
    LaunchedEffect(uiState.loginSuccessful) {
        if (uiState.loginSuccessful) {
            onLoginSuccess()
        }
    }

    // Initialize biometric availability and session validation on screen start
    LaunchedEffect(Unit) {
        viewModel.checkBiometricAvailability()
        viewModel.validateSession()
    }

    // Show biometric prompt if user has biometric setup and session exists
    LaunchedEffect(uiState.biometricSetup, isBiometricEnabled) {
        if (uiState.biometricAvailable && uiState.biometricSetup && isBiometricEnabled && context is FragmentActivity) {
            // Only show biometric prompt if user has existing session
            viewModel.authRepository.currentUser.collect { user ->
                if (user != null) {
                    viewModel.authenticateWithBiometric(context)
                }
            }
        }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        // App Logo/Title
        Text(
            text = "PLS Travels",
            fontSize = 32.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary
        )
        
        Text(
            text = "Driver Portal",
            fontSize = 18.sp,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
            modifier = Modifier.padding(bottom = 48.dp)
        )

        if (!uiState.otpSent) {
            PhoneNumberInput(
                viewModel = viewModel,
                uiState = uiState,
                onSendOtp = viewModel::sendOtp,
                isLoading = uiState.isLoading,
                error = uiState.error,
                onClearError = viewModel::clearError
            )
        } else {
            OtpVerification(
                viewModel = viewModel,
                uiState = uiState,
                phone = uiState.currentPhone,
                onVerifyOtp = viewModel::verifyOtp,
                onResendOtp = { viewModel.sendOtp(uiState.currentPhone) },
                onBackToPhone = viewModel::resetOtpFlow,
                isLoading = uiState.isLoading,
                error = uiState.error,
                message = uiState.message,
                onClearError = viewModel::clearError,
                onClearMessage = viewModel::clearMessage
            )
            
            // Show biometric setup option after successful login
            if (uiState.biometricAvailable && !uiState.biometricSetup && message?.contains("successful", ignoreCase = true) == true) {
                Spacer(modifier = Modifier.height(16.dp))
                
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.1f)
                    )
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = "🔒 Enable Biometric Login",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Medium,
                            color = MaterialTheme.colorScheme.primary
                        )
                        
                        Text(
                            text = "Set up fingerprint or face unlock for faster, secure access",
                            fontSize = 14.sp,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                            textAlign = TextAlign.Center,
                            modifier = Modifier.padding(top = 4.dp, bottom = 12.dp)
                        )
                        
                        val context = LocalContext.current
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceEvenly
                        ) {
                            OutlinedButton(
                                onClick = { /* Skip for now */ },
                                enabled = !isLoading,
                                modifier = Modifier.weight(1f)
                            ) {
                                Text("Skip")
                            }
                            
                            Spacer(modifier = Modifier.width(8.dp))
                            
                            Button(
                                onClick = {
                                    if (context is FragmentActivity) {
                                        viewModel.setupBiometric(context)
                                    }
                                },
                                enabled = !isLoading,
                                modifier = Modifier.weight(1f)
                            ) {
                                Text("Enable")
                            }
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PhoneNumberInput(
    viewModel: AuthViewModel,
    uiState: AuthUiState,
    onSendOtp: (String) -> Unit,
    isLoading: Boolean,
    error: String?,
    onClearError: () -> Unit
) {
    var phoneNumber by remember { mutableStateOf("") }

    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier.padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "Enter Your Phone Number",
                fontSize = 20.sp,
                fontWeight = FontWeight.Medium,
                modifier = Modifier.padding(bottom = 16.dp)
            )

            OutlinedTextField(
                value = phoneNumber,
                onValueChange = { 
                    phoneNumber = it.filter { char -> char.isDigit() }
                    if (error != null) onClearError()
                },
                label = { Text("Phone Number") },
                placeholder = { Text("10-digit mobile number") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                isError = error != null
            )

            if (error != null) {
                Text(
                    text = error,
                    color = MaterialTheme.colorScheme.error,
                    fontSize = 14.sp,
                    modifier = Modifier.padding(top = 4.dp)
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            Button(
                onClick = { onSendOtp(phoneNumber) },
                enabled = !isLoading && phoneNumber.length >= 10,
                modifier = Modifier.fillMaxWidth()
            ) {
                if (isLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                } else {
                    Text("Send OTP")
                }
            }

            val context = LocalContext.current
            
            // Show biometric authentication option only if available and previously set up
            if (uiState.biometricAvailable && uiState.biometricSetup) {
                Spacer(modifier = Modifier.height(12.dp))
                
                OutlinedButton(
                    onClick = {
                        if (context is FragmentActivity) {
                            viewModel.authenticateWithBiometric(context)
                        }
                    },
                    enabled = !isLoading,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Use Biometric Authentication")
                }
            }
            
            // Show biometric setup hint if available but not set up
            if (uiState.biometricAvailable && !uiState.biometricSetup) {
                Spacer(modifier = Modifier.height(8.dp))
                
                Text(
                    text = "💡 Enable biometric login after signing in",
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun OtpVerification(
    viewModel: AuthViewModel,
    uiState: AuthUiState,
    phone: String,
    onVerifyOtp: (String) -> Unit,
    onResendOtp: () -> Unit,
    onBackToPhone: () -> Unit,
    isLoading: Boolean,
    error: String?,
    message: String?,
    onClearError: () -> Unit,
    onClearMessage: () -> Unit
) {
    var otp by remember { mutableStateOf("") }
    
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier.padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "Enter OTP",
                fontSize = 20.sp,
                fontWeight = FontWeight.Medium
            )
            
            Text(
                text = "OTP sent to $phone",
                fontSize = 14.sp,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(vertical = 8.dp)
            )

            OutlinedTextField(
                value = otp,
                onValueChange = { 
                    if (it.length <= 6 && it.all { char -> char.isDigit() }) {
                        otp = it
                        if (error != null) onClearError()
                    }
                },
                label = { Text("6-digit OTP") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                isError = error != null
            )

            if (error != null) {
                Text(
                    text = error,
                    color = MaterialTheme.colorScheme.error,
                    fontSize = 14.sp,
                    modifier = Modifier.padding(top = 4.dp)
                )
            }

            if (message != null) {
                Text(
                    text = message,
                    color = MaterialTheme.colorScheme.primary,
                    fontSize = 14.sp,
                    modifier = Modifier.padding(top = 4.dp)
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            Button(
                onClick = { onVerifyOtp(otp) },
                enabled = !isLoading && otp.length == 6,
                modifier = Modifier.fillMaxWidth()
            ) {
                if (isLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                } else {
                    Text("Verify OTP")
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                TextButton(
                    onClick = onBackToPhone,
                    enabled = !isLoading
                ) {
                    Text("Change Number")
                }
                
                TextButton(
                    onClick = onResendOtp,
                    enabled = !isLoading
                ) {
                    Text("Resend OTP")
                }
            }
        }
    }
}