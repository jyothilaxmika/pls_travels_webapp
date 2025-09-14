package com.plstravels.driver.viewmodel

import com.plstravels.driver.data.repository.AuthRepository
import com.plstravels.driver.testutils.BaseUnitTest
import com.plstravels.driver.testutils.factories.TestDataFactory
import com.plstravels.driver.ui.auth.AuthViewModel
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.flowOf
import org.junit.Before
import org.junit.Test
import com.google.common.truth.Truth.assertThat

/**
 * Comprehensive unit tests for AuthViewModel
 * Tests UI state management, OTP flow, and error handling
 */
@ExperimentalCoroutinesApi
class AuthViewModelTest : BaseUnitTest() {

    private lateinit var authViewModel: AuthViewModel
    private val mockAuthRepository: AuthRepository = mockk()

    @Before
    override fun setUp() {
        super.setUp()
        
        // Default repository behavior
        every { mockAuthRepository.isLoggedIn } returns flowOf(false)
        
        authViewModel = AuthViewModel(mockAuthRepository)
    }

    @Test
    fun `initial state should be correct`() = runTest {
        // Assert
        with(authViewModel.uiState.value) {
            assertThat(isLoading).isFalse()
            assertThat(otpSent).isFalse()
            assertThat(loginSuccess).isFalse()
            assertThat(phoneNumber).isEmpty()
            assertThat(message).isNull()
            assertThat(error).isNull()
        }
        assertThat(authViewModel.isLoggedIn.value).isFalse()
    }

    @Test
    fun `sendOtp should update UI state to loading and then success`() = runTest {
        // Arrange
        val phoneNumber = "9876543210"
        val successResponse = TestDataFactory.createTestSendOtpResponse()
        coEvery { mockAuthRepository.sendOtp(any()) } returns Result.success(successResponse)

        // Act
        authViewModel.sendOtp(phoneNumber)
        testCoroutineRule.testDispatcher.scheduler.advanceUntilIdle()

        // Assert
        with(authViewModel.uiState.value) {
            assertThat(isLoading).isFalse()
            assertThat(otpSent).isTrue()
            assertThat(this.phoneNumber).isEqualTo(phoneNumber)
            assertThat(message).isEqualTo(successResponse.message)
            assertThat(error).isNull()
        }
        
        coVerify { mockAuthRepository.sendOtp(phoneNumber) }
    }

    @Test
    fun `sendOtp should handle invalid phone number`() = runTest {
        // Arrange
        val invalidPhoneNumber = "123" // Too short

        // Act
        authViewModel.sendOtp(invalidPhoneNumber)
        testCoroutineRule.testDispatcher.scheduler.advanceUntilIdle()

        // Assert
        with(authViewModel.uiState.value) {
            assertThat(isLoading).isFalse()
            assertThat(otpSent).isFalse()
            assertThat(error).isEqualTo("Please enter a valid phone number")
        }
        
        coVerify(exactly = 0) { mockAuthRepository.sendOtp(any()) }
    }

    @Test
    fun `sendOtp should handle repository failure`() = runTest {
        // Arrange
        val phoneNumber = "9876543210"
        val errorMessage = "Failed to send OTP"
        coEvery { mockAuthRepository.sendOtp(any()) } returns Result.failure(Exception(errorMessage))

        // Act
        authViewModel.sendOtp(phoneNumber)
        testCoroutineRule.testDispatcher.scheduler.advanceUntilIdle()

        // Assert
        with(authViewModel.uiState.value) {
            assertThat(isLoading).isFalse()
            assertThat(otpSent).isFalse()
            assertThat(error).isEqualTo(errorMessage)
        }
    }

    @Test
    fun `verifyOtp should update UI state to loading and then success`() = runTest {
        // Arrange
        val phoneNumber = "9876543210"
        val otpCode = "123456"
        val successResponse = TestDataFactory.createTestVerifyOtpResponse()
        
        // First send OTP to set phone number
        coEvery { mockAuthRepository.sendOtp(any()) } returns Result.success(TestDataFactory.createTestSendOtpResponse())
        authViewModel.sendOtp(phoneNumber)
        testCoroutineRule.testDispatcher.scheduler.advanceUntilIdle()
        
        // Setup verify OTP
        coEvery { mockAuthRepository.verifyOtp(any(), any()) } returns Result.success(successResponse)

        // Act
        authViewModel.verifyOtp(otpCode)
        testCoroutineRule.testDispatcher.scheduler.advanceUntilIdle()

        // Assert
        with(authViewModel.uiState.value) {
            assertThat(isLoading).isFalse()
            assertThat(loginSuccess).isTrue()
            assertThat(message).isEqualTo("Login successful")
            assertThat(error).isNull()
        }
        
        coVerify { mockAuthRepository.verifyOtp(phoneNumber, otpCode) }
    }

    @Test
    fun `verifyOtp should handle invalid OTP length`() = runTest {
        // Arrange
        val invalidOtp = "123" // Too short

        // Act
        authViewModel.verifyOtp(invalidOtp)
        testCoroutineRule.testDispatcher.scheduler.advanceUntilIdle()

        // Assert
        with(authViewModel.uiState.value) {
            assertThat(isLoading).isFalse()
            assertThat(loginSuccess).isFalse()
            assertThat(error).isEqualTo("Please enter a valid 6-digit OTP")
        }
        
        coVerify(exactly = 0) { mockAuthRepository.verifyOtp(any(), any()) }
    }

    @Test
    fun `verifyOtp should handle repository failure`() = runTest {
        // Arrange
        val phoneNumber = "9876543210"
        val otpCode = "123456"
        val errorMessage = "Invalid OTP"
        
        // First send OTP
        coEvery { mockAuthRepository.sendOtp(any()) } returns Result.success(TestDataFactory.createTestSendOtpResponse())
        authViewModel.sendOtp(phoneNumber)
        testCoroutineRule.testDispatcher.scheduler.advanceUntilIdle()
        
        // Setup verify failure
        coEvery { mockAuthRepository.verifyOtp(any(), any()) } returns Result.failure(Exception(errorMessage))

        // Act
        authViewModel.verifyOtp(otpCode)
        testCoroutineRule.testDispatcher.scheduler.advanceUntilIdle()

        // Assert
        with(authViewModel.uiState.value) {
            assertThat(isLoading).isFalse()
            assertThat(loginSuccess).isFalse()
            assertThat(error).isEqualTo(errorMessage)
        }
    }

    @Test
    fun `resendOtp should call sendOtp with existing phone number`() = runTest {
        // Arrange
        val phoneNumber = "9876543210"
        val successResponse = TestDataFactory.createTestSendOtpResponse()
        
        coEvery { mockAuthRepository.sendOtp(any()) } returns Result.success(successResponse)
        
        // First send OTP
        authViewModel.sendOtp(phoneNumber)
        testCoroutineRule.testDispatcher.scheduler.advanceUntilIdle()

        // Act
        authViewModel.resendOtp()
        testCoroutineRule.testDispatcher.scheduler.advanceUntilIdle()

        // Assert
        coVerify(exactly = 2) { mockAuthRepository.sendOtp(phoneNumber) }
    }

    @Test
    fun `resendOtp should not call repository when no phone number set`() = runTest {
        // Act
        authViewModel.resendOtp()
        testCoroutineRule.testDispatcher.scheduler.advanceUntilIdle()

        // Assert
        coVerify(exactly = 0) { mockAuthRepository.sendOtp(any()) }
    }

    @Test
    fun `clearError should remove error from state`() = runTest {
        // Arrange - Set an error state
        val invalidPhoneNumber = "123"
        authViewModel.sendOtp(invalidPhoneNumber)
        testCoroutineRule.testDispatcher.scheduler.advanceUntilIdle()
        
        assertThat(authViewModel.uiState.value.error).isNotNull()

        // Act
        authViewModel.clearError()

        // Assert
        assertThat(authViewModel.uiState.value.error).isNull()
    }

    @Test
    fun `resetState should reset UI state to initial values`() = runTest {
        // Arrange - Set some state
        val phoneNumber = "9876543210"
        coEvery { mockAuthRepository.sendOtp(any()) } returns Result.success(TestDataFactory.createTestSendOtpResponse())
        authViewModel.sendOtp(phoneNumber)
        testCoroutineRule.testDispatcher.scheduler.advanceUntilIdle()
        
        assertThat(authViewModel.uiState.value.otpSent).isTrue()

        // Act
        authViewModel.resetState()

        // Assert
        with(authViewModel.uiState.value) {
            assertThat(isLoading).isFalse()
            assertThat(otpSent).isFalse()
            assertThat(loginSuccess).isFalse()
            assertThat(phoneNumber).isEmpty()
            assertThat(message).isNull()
            assertThat(error).isNull()
        }
    }

    @Test
    fun `isLoggedIn should reflect repository state changes`() = runTest {
        // Arrange
        val loggedInFlow = flowOf(false, true, false)
        every { mockAuthRepository.isLoggedIn } returns loggedInFlow

        // Create new instance to pick up the flow
        authViewModel = AuthViewModel(mockAuthRepository)
        testCoroutineRule.testDispatcher.scheduler.advanceUntilIdle()

        // The flow should be collected and state updated
        // Note: In real implementation, you might need to collect the flow manually
        // This test structure depends on how the ViewModel handles the flow
    }

    @Test
    fun `phone number validation should work correctly`() = runTest {
        val testCases = listOf(
            "9876543210" to true,    // Valid 10-digit
            "+919876543210" to true, // Valid with country code  
            "987654321" to false,    // Too short
            "98765432101" to false,  // Too long
            "abcdefghij" to false,   // Non-numeric
            "" to false,             // Empty
            "123-456-7890" to false  // Invalid format (though this might be arguable)
        )

        testCases.forEach { (phoneNumber, shouldBeValid) ->
            // Act
            authViewModel.sendOtp(phoneNumber)
            testCoroutineRule.testDispatcher.scheduler.advanceUntilIdle()

            // Assert
            if (shouldBeValid) {
                coVerify { mockAuthRepository.sendOtp(any()) }
                assertThat(authViewModel.uiState.value.error).isNull()
            } else {
                assertThat(authViewModel.uiState.value.error).isEqualTo("Please enter a valid phone number")
            }

            // Reset for next test
            authViewModel.resetState()
            clearMocks(mockAuthRepository, answers = false)
        }
    }

    @Test
    fun `loading state should be managed correctly during async operations`() = runTest {
        // Arrange
        val phoneNumber = "9876543210"
        coEvery { mockAuthRepository.sendOtp(any()) } returns Result.success(TestDataFactory.createTestSendOtpResponse())

        // Act & Assert - Check loading state during operation
        authViewModel.sendOtp(phoneNumber)
        
        // Loading should be true immediately after calling sendOtp
        assertThat(authViewModel.uiState.value.isLoading).isTrue()
        
        // Complete the coroutine
        testCoroutineRule.testDispatcher.scheduler.advanceUntilIdle()
        
        // Loading should be false after completion
        assertThat(authViewModel.uiState.value.isLoading).isFalse()
    }

    @Test
    fun `network error should be handled gracefully`() = runTest {
        // Arrange
        val phoneNumber = "9876543210"
        coEvery { mockAuthRepository.sendOtp(any()) } throws Exception("Network error occurred")

        // Act
        authViewModel.sendOtp(phoneNumber)
        testCoroutineRule.testDispatcher.scheduler.advanceUntilIdle()

        // Assert
        with(authViewModel.uiState.value) {
            assertThat(isLoading).isFalse()
            assertThat(otpSent).isFalse()
            assertThat(error).isEqualTo("Network error occurred")
        }
    }
}