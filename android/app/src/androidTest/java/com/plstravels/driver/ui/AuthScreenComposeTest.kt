package com.plstravels.driver.ui

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.plstravels.driver.ui.auth.AuthScreen
import com.plstravels.driver.ui.auth.AuthUiState
import com.plstravels.driver.ui.theme.PLSDriverTheme
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * UI tests for AuthScreen using Compose testing framework
 * Tests user interactions, state changes, and UI behavior
 */
@RunWith(AndroidJUnit4::class)
class AuthScreenComposeTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    @Test
    fun authScreen_initialState_showsPhoneInputAndSendButton() {
        // Arrange
        val initialState = AuthUiState()
        
        composeTestRule.setContent {
            PLSDriverTheme {
                AuthScreen(
                    uiState = initialState,
                    onSendOtp = { },
                    onVerifyOtp = { },
                    onResendOtp = { },
                    onClearError = { }
                )
            }
        }

        // Assert
        composeTestRule
            .onNodeWithTag("input-phone")
            .assertExists()
            .assertIsDisplayed()

        composeTestRule
            .onNodeWithTag("button-send-otp")
            .assertExists()
            .assertIsDisplayed()
            .assertIsEnabled()

        composeTestRule
            .onNodeWithTag("input-otp")
            .assertDoesNotExist()
    }

    @Test
    fun authScreen_afterOtpSent_showsOtpInputAndVerifyButton() {
        // Arrange
        val otpSentState = AuthUiState(
            otpSent = true,
            phoneNumber = "9876543210",
            message = "OTP sent successfully"
        )

        composeTestRule.setContent {
            PLSDriverTheme {
                AuthScreen(
                    uiState = otpSentState,
                    onSendOtp = { },
                    onVerifyOtp = { },
                    onResendOtp = { },
                    onClearError = { }
                )
            }
        }

        // Assert
        composeTestRule
            .onNodeWithTag("input-otp")
            .assertExists()
            .assertIsDisplayed()

        composeTestRule
            .onNodeWithTag("button-verify-otp")
            .assertExists()
            .assertIsDisplayed()

        composeTestRule
            .onNodeWithTag("button-resend-otp")
            .assertExists()
            .assertIsDisplayed()

        composeTestRule
            .onNodeWithText("OTP sent successfully")
            .assertIsDisplayed()
    }

    @Test
    fun authScreen_phoneInput_acceptsValidInput() {
        // Arrange
        val initialState = AuthUiState()
        var capturedPhoneNumber = ""
        
        composeTestRule.setContent {
            PLSDriverTheme {
                AuthScreen(
                    uiState = initialState,
                    onSendOtp = { capturedPhoneNumber = it },
                    onVerifyOtp = { },
                    onResendOtp = { },
                    onClearError = { }
                )
            }
        }

        // Act
        composeTestRule
            .onNodeWithTag("input-phone")
            .performTextInput("9876543210")

        composeTestRule
            .onNodeWithTag("button-send-otp")
            .performClick()

        // Assert
        assert(capturedPhoneNumber == "9876543210")
    }

    @Test
    fun authScreen_otpInput_acceptsValidInput() {
        // Arrange
        val otpSentState = AuthUiState(otpSent = true, phoneNumber = "9876543210")
        var capturedOtp = ""
        
        composeTestRule.setContent {
            PLSDriverTheme {
                AuthScreen(
                    uiState = otpSentState,
                    onSendOtp = { },
                    onVerifyOtp = { capturedOtp = it },
                    onResendOtp = { },
                    onClearError = { }
                )
            }
        }

        // Act
        composeTestRule
            .onNodeWithTag("input-otp")
            .performTextInput("123456")

        composeTestRule
            .onNodeWithTag("button-verify-otp")
            .performClick()

        // Assert
        assert(capturedOtp == "123456")
    }

    @Test
    fun authScreen_loadingState_showsProgressIndicator() {
        // Arrange
        val loadingState = AuthUiState(isLoading = true)
        
        composeTestRule.setContent {
            PLSDriverTheme {
                AuthScreen(
                    uiState = loadingState,
                    onSendOtp = { },
                    onVerifyOtp = { },
                    onResendOtp = { },
                    onClearError = { }
                )
            }
        }

        // Assert
        composeTestRule
            .onNodeWithTag("progress-indicator")
            .assertExists()
            .assertIsDisplayed()

        composeTestRule
            .onNodeWithTag("button-send-otp")
            .assertIsNotEnabled()
    }

    @Test
    fun authScreen_errorState_showsErrorMessage() {
        // Arrange
        val errorState = AuthUiState(error = "Invalid phone number")
        var errorCleared = false
        
        composeTestRule.setContent {
            PLSDriverTheme {
                AuthScreen(
                    uiState = errorState,
                    onSendOtp = { },
                    onVerifyOtp = { },
                    onResendOtp = { },
                    onClearError = { errorCleared = true }
                )
            }
        }

        // Assert
        composeTestRule
            .onNodeWithText("Invalid phone number")
            .assertIsDisplayed()

        // Act - Error should be dismissible
        composeTestRule
            .onNodeWithTag("error-dismiss")
            .performClick()

        // Assert
        assert(errorCleared)
    }

    @Test
    fun authScreen_successState_showsSuccessMessage() {
        // Arrange
        val successState = AuthUiState(
            loginSuccess = true,
            message = "Login successful"
        )
        
        composeTestRule.setContent {
            PLSDriverTheme {
                AuthScreen(
                    uiState = successState,
                    onSendOtp = { },
                    onVerifyOtp = { },
                    onResendOtp = { },
                    onClearError = { }
                )
            }
        }

        // Assert
        composeTestRule
            .onNodeWithText("Login successful")
            .assertIsDisplayed()
    }

    @Test
    fun authScreen_resendOtpButton_callsCorrectCallback() {
        // Arrange
        val otpSentState = AuthUiState(otpSent = true, phoneNumber = "9876543210")
        var resendCalled = false
        
        composeTestRule.setContent {
            PLSDriverTheme {
                AuthScreen(
                    uiState = otpSentState,
                    onSendOtp = { },
                    onVerifyOtp = { },
                    onResendOtp = { resendCalled = true },
                    onClearError = { }
                )
            }
        }

        // Act
        composeTestRule
            .onNodeWithTag("button-resend-otp")
            .performClick()

        // Assert
        assert(resendCalled)
    }

    @Test
    fun authScreen_phoneInputValidation_showsCorrectHints() {
        // Arrange
        val initialState = AuthUiState()
        
        composeTestRule.setContent {
            PLSDriverTheme {
                AuthScreen(
                    uiState = initialState,
                    onSendOtp = { },
                    onVerifyOtp = { },
                    onResendOtp = { },
                    onClearError = { }
                )
            }
        }

        // Assert
        composeTestRule
            .onNodeWithText("Enter your phone number")
            .assertIsDisplayed()

        composeTestRule
            .onNodeWithText("Enter 10-digit mobile number")
            .assertIsDisplayed()
    }

    @Test
    fun authScreen_otpInputValidation_showsCorrectHints() {
        // Arrange
        val otpSentState = AuthUiState(otpSent = true, phoneNumber = "9876543210")
        
        composeTestRule.setContent {
            PLSDriverTheme {
                AuthScreen(
                    uiState = otpSentState,
                    onSendOtp = { },
                    onVerifyOtp = { },
                    onResendOtp = { },
                    onClearError = { }
                )
            }
        }

        // Assert
        composeTestRule
            .onNodeWithText("Enter OTP")
            .assertIsDisplayed()

        composeTestRule
            .onNodeWithText("Enter 6-digit OTP sent to 9876543210")
            .assertIsDisplayed()
    }

    @Test
    fun authScreen_keyboardActions_workCorrectly() {
        // Arrange
        val initialState = AuthUiState()
        var sendOtpCalled = false
        
        composeTestRule.setContent {
            PLSDriverTheme {
                AuthScreen(
                    uiState = initialState,
                    onSendOtp = { sendOtpCalled = true },
                    onVerifyOtp = { },
                    onResendOtp = { },
                    onClearError = { }
                )
            }
        }

        // Act - Type phone number and press IME action
        composeTestRule
            .onNodeWithTag("input-phone")
            .performTextInput("9876543210")
            .performImeAction()

        // Assert
        assert(sendOtpCalled)
    }

    @Test
    fun authScreen_accessibility_hasCorrectContentDescriptions() {
        // Arrange
        val initialState = AuthUiState()
        
        composeTestRule.setContent {
            PLSDriverTheme {
                AuthScreen(
                    uiState = initialState,
                    onSendOtp = { },
                    onVerifyOtp = { },
                    onResendOtp = { },
                    onClearError = { }
                )
            }
        }

        // Assert
        composeTestRule
            .onNodeWithTag("input-phone")
            .assert(hasContentDescription())

        composeTestRule
            .onNodeWithTag("button-send-otp")
            .assert(hasContentDescription())
    }

    @Test
    fun authScreen_multipleStatesTransition_worksCorrectly() {
        // This test verifies smooth transition between different UI states
        
        // Start with initial state
        var currentState = AuthUiState()
        
        composeTestRule.setContent {
            PLSDriverTheme {
                AuthScreen(
                    uiState = currentState,
                    onSendOtp = { },
                    onVerifyOtp = { },
                    onResendOtp = { },
                    onClearError = { }
                )
            }
        }

        // Verify initial state
        composeTestRule
            .onNodeWithTag("input-phone")
            .assertIsDisplayed()

        // Transition to loading state
        currentState = currentState.copy(isLoading = true)
        composeTestRule.setContent {
            PLSDriverTheme {
                AuthScreen(
                    uiState = currentState,
                    onSendOtp = { },
                    onVerifyOtp = { },
                    onResendOtp = { },
                    onClearError = { }
                )
            }
        }

        composeTestRule
            .onNodeWithTag("progress-indicator")
            .assertIsDisplayed()

        // Transition to OTP sent state
        currentState = AuthUiState(otpSent = true, phoneNumber = "9876543210")
        composeTestRule.setContent {
            PLSDriverTheme {
                AuthScreen(
                    uiState = currentState,
                    onSendOtp = { },
                    onVerifyOtp = { },
                    onResendOtp = { },
                    onClearError = { }
                )
            }
        }

        composeTestRule
            .onNodeWithTag("input-otp")
            .assertIsDisplayed()

        // Transition to success state
        currentState = currentState.copy(loginSuccess = true, message = "Login successful")
        composeTestRule.setContent {
            PLSDriverTheme {
                AuthScreen(
                    uiState = currentState,
                    onSendOtp = { },
                    onVerifyOtp = { },
                    onResendOtp = { },
                    onClearError = { }
                )
            }
        }

        composeTestRule
            .onNodeWithText("Login successful")
            .assertIsDisplayed()
    }
}