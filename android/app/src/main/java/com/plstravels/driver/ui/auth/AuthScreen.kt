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
import androidx.hilt.navigation.compose.hiltViewModel

/**
 * Authentication screen with phone number and OTP input
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AuthScreen(
    authViewModel: AuthViewModel = hiltViewModel(),
    onLoginSuccess: () -> Unit
) {
    val uiState by authViewModel.uiState.collectAsState()
    var phoneNumber by remember { mutableStateOf("") }
    var otpCode by remember { mutableStateOf("") }
    
    // Navigate on successful login
    LaunchedEffect(uiState.loginSuccess) {
        if (uiState.loginSuccess) {
            onLoginSuccess()
        }
    }
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        
        // App Title
        Text(
            text = "PLS Travels",
            style = MaterialTheme.typography.headlineLarge,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary
        )
        
        Text(
            text = "Driver App",
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
        )
        
        Spacer(modifier = Modifier.height(48.dp))
        
        if (!uiState.otpSent) {
            // Phone Number Input
            PhoneNumberSection(
                phoneNumber = phoneNumber,
                onPhoneNumberChange = { phoneNumber = it },
                onSendOtp = { authViewModel.sendOtp(phoneNumber) },
                isLoading = uiState.isLoading
            )
        } else {
            // OTP Input
            OtpSection(
                phoneNumber = uiState.phoneNumber,
                otpCode = otpCode,
                onOtpCodeChange = { otpCode = it },
                onVerifyOtp = { authViewModel.verifyOtp(otpCode) },
                onResendOtp = { authViewModel.resendOtp() },
                isLoading = uiState.isLoading
            )
        }
        
        // Error Message
        uiState.error?.let { error ->
            Spacer(modifier = Modifier.height(16.dp))
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.errorContainer
                )
            ) {
                Text(
                    text = error,
                    modifier = Modifier.padding(16.dp),
                    color = MaterialTheme.colorScheme.onErrorContainer,
                    textAlign = TextAlign.Center
                )
            }
        }
        
        // Success Message
        uiState.message?.let { message ->
            Spacer(modifier = Modifier.height(16.dp))
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer
                )
            ) {
                Text(
                    text = message,
                    modifier = Modifier.padding(16.dp),
                    color = MaterialTheme.colorScheme.onPrimaryContainer,
                    textAlign = TextAlign.Center
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PhoneNumberSection(
    phoneNumber: String,
    onPhoneNumberChange: (String) -> Unit,
    onSendOtp: () -> Unit,
    isLoading: Boolean
) {
    Text(
        text = "Enter your phone number",
        style = MaterialTheme.typography.titleMedium,
        textAlign = TextAlign.Center
    )
    
    Spacer(modifier = Modifier.height(16.dp))
    
    OutlinedTextField(
        value = phoneNumber,
        onValueChange = onPhoneNumberChange,
        label = { Text("Phone Number") },
        placeholder = { Text("10-digit mobile number") },
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
        modifier = Modifier.fillMaxWidth(),
        singleLine = true
    )
    
    Spacer(modifier = Modifier.height(24.dp))
    
    Button(
        onClick = onSendOtp,
        enabled = !isLoading && phoneNumber.isNotEmpty(),
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
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun OtpSection(
    phoneNumber: String,
    otpCode: String,
    onOtpCodeChange: (String) -> Unit,
    onVerifyOtp: () -> Unit,
    onResendOtp: () -> Unit,
    isLoading: Boolean
) {
    Text(
        text = "Enter OTP sent to",
        style = MaterialTheme.typography.titleMedium,
        textAlign = TextAlign.Center
    )
    
    Text(
        text = phoneNumber,
        style = MaterialTheme.typography.bodyLarge,
        fontWeight = FontWeight.Medium,
        color = MaterialTheme.colorScheme.primary,
        textAlign = TextAlign.Center
    )
    
    Spacer(modifier = Modifier.height(16.dp))
    
    OutlinedTextField(
        value = otpCode,
        onValueChange = { if (it.length <= 6) onOtpCodeChange(it) },
        label = { Text("OTP Code") },
        placeholder = { Text("6-digit code") },
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
        modifier = Modifier.fillMaxWidth(),
        singleLine = true
    )
    
    Spacer(modifier = Modifier.height(24.dp))
    
    Button(
        onClick = onVerifyOtp,
        enabled = !isLoading && otpCode.length == 6,
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
    
    Spacer(modifier = Modifier.height(16.dp))
    
    TextButton(
        onClick = onResendOtp,
        enabled = !isLoading
    ) {
        Text("Resend OTP")
    }
}