package com.plstravels.driver.repository

import android.content.Context
import com.plstravels.driver.data.local.TokenManager
import com.plstravels.driver.data.network.ApiService
import com.plstravels.driver.data.repository.AuthRepository
import com.plstravels.driver.testutils.BaseUnitTest
import com.plstravels.driver.testutils.factories.TestDataFactory
import com.plstravels.driver.testutils.shouldBeFailure
import com.plstravels.driver.testutils.shouldBeSuccess
import com.plstravels.driver.testutils.shouldHaveError
import com.plstravels.driver.testutils.shouldHaveValue
import io.mockk.*
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.flowOf
import org.junit.Before
import org.junit.Test
import retrofit2.Response

/**
 * Comprehensive unit tests for AuthRepository
 * Tests OTP flow, token management, and error handling
 */
@ExperimentalCoroutinesApi
class AuthRepositoryTest : BaseUnitTest() {

    private lateinit var authRepository: AuthRepository
    private val mockApiService: ApiService = mockk()
    private val mockTokenManager: TokenManager = mockk()
    private val mockContext: Context = mockk()

    @Before
    override fun setUp() {
        super.setUp()
        
        // Mock Context for device ID
        every { mockContext.contentResolver } returns mockk()
        mockkStatic(android.provider.Settings.Secure::class)
        every { 
            android.provider.Settings.Secure.getString(any(), any()) 
        } returns "test_device_123"

        // Default TokenManager behavior
        every { mockTokenManager.isLoggedIn } returns flowOf(false)
        coEvery { mockTokenManager.saveTokens(any(), any(), any(), any(), any(), any()) } just Runs
        coEvery { mockTokenManager.clearTokens() } just Runs
        coEvery { mockTokenManager.updateAccessToken(any(), any()) } just Runs
        coEvery { mockTokenManager.getCurrentUserId() } returns 1
        coEvery { mockTokenManager.getCurrentUsername() } returns "test_user"
        coEvery { mockTokenManager.getCurrentUserRole() } returns "driver"

        authRepository = AuthRepository(mockApiService, mockTokenManager, mockContext)
    }

    @Test
    fun `sendOtp should format phone number correctly and return success`() = runTest {
        // Arrange
        val phoneNumber = "9876543210"
        val expectedFormattedNumber = "+919876543210"
        val expectedResponse = TestDataFactory.createTestSendOtpResponse()
        
        coEvery { mockApiService.sendOtp(any()) } returns Response.success(expectedResponse)

        // Act
        val result = authRepository.sendOtp(phoneNumber)

        // Assert
        result.shouldBeSuccess()
        result.shouldHaveValue(expectedResponse)
        
        coVerify { 
            mockApiService.sendOtp(
                match { request -> request.phoneNumber == expectedFormattedNumber }
            )
        }
    }

    @Test
    fun `sendOtp should handle phone number with country code`() = runTest {
        // Arrange
        val phoneNumber = "+919876543210"
        val expectedResponse = TestDataFactory.createTestSendOtpResponse()
        
        coEvery { mockApiService.sendOtp(any()) } returns Response.success(expectedResponse)

        // Act
        val result = authRepository.sendOtp(phoneNumber)

        // Assert
        result.shouldBeSuccess()
        coVerify { 
            mockApiService.sendOtp(
                match { request -> request.phoneNumber == phoneNumber }
            )
        }
    }

    @Test
    fun `sendOtp should return failure when API returns error`() = runTest {
        // Arrange
        val phoneNumber = "9876543210"
        val errorResponse = TestDataFactory.createTestSendOtpResponse(false, "Failed to send OTP")
        
        coEvery { mockApiService.sendOtp(any()) } returns Response.success(errorResponse)

        // Act
        val result = authRepository.sendOtp(phoneNumber)

        // Assert
        result.shouldBeFailure()
        result.shouldHaveError("Failed to send OTP")
    }

    @Test
    fun `sendOtp should return failure when network call fails`() = runTest {
        // Arrange
        val phoneNumber = "9876543210"
        
        coEvery { mockApiService.sendOtp(any()) } throws Exception("Network error")

        // Act
        val result = authRepository.sendOtp(phoneNumber)

        // Assert
        result.shouldBeFailure()
        result.shouldHaveError("Network error")
    }

    @Test
    fun `verifyOtp should save tokens and return success`() = runTest {
        // Arrange
        val phoneNumber = "+919876543210"
        val otpCode = "123456"
        val testUser = TestDataFactory.createTestUser()
        val expectedResponse = TestDataFactory.createTestVerifyOtpResponse(
            user = testUser,
            accessToken = "test_access_token",
            refreshToken = "test_refresh_token"
        )
        
        coEvery { mockApiService.verifyOtp(any()) } returns Response.success(expectedResponse)

        // Act
        val result = authRepository.verifyOtp(phoneNumber, otpCode)

        // Assert
        result.shouldBeSuccess()
        result.shouldHaveValue(expectedResponse)
        
        coVerify { 
            mockTokenManager.saveTokens(
                "test_access_token",
                "test_refresh_token",
                testUser.id,
                testUser.username,
                testUser.role,
                3600
            )
        }
    }

    @Test
    fun `verifyOtp should include device ID in request`() = runTest {
        // Arrange
        val phoneNumber = "+919876543210"
        val otpCode = "123456"
        val expectedResponse = TestDataFactory.createTestVerifyOtpResponse()
        
        coEvery { mockApiService.verifyOtp(any()) } returns Response.success(expectedResponse)

        // Act
        val result = authRepository.verifyOtp(phoneNumber, otpCode)

        // Assert
        result.shouldBeSuccess()
        coVerify { 
            mockApiService.verifyOtp(
                match { request -> 
                    request.phoneNumber == phoneNumber &&
                    request.otpCode == otpCode &&
                    request.deviceId == "test_device_123"
                }
            )
        }
    }

    @Test
    fun `verifyOtp should return failure for invalid OTP`() = runTest {
        // Arrange
        val phoneNumber = "+919876543210"
        val otpCode = "000000"
        val errorResponse = TestDataFactory.createTestVerifyOtpResponse(false, "Invalid OTP")
        
        coEvery { mockApiService.verifyOtp(any()) } returns Response.success(errorResponse)

        // Act
        val result = authRepository.verifyOtp(phoneNumber, otpCode)

        // Assert
        result.shouldBeFailure()
        result.shouldHaveError("Invalid OTP")
        
        coVerify(exactly = 0) { mockTokenManager.saveTokens(any(), any(), any(), any(), any(), any()) }
    }

    @Test
    fun `refreshToken should update access token on success`() = runTest {
        // Arrange
        val refreshResponse = TestDataFactory.createTestRefreshTokenResponse(
            accessToken = "new_access_token"
        )
        
        coEvery { mockApiService.refreshToken() } returns Response.success(refreshResponse)

        // Act
        val result = authRepository.refreshToken()

        // Assert
        result.shouldBeSuccess()
        result.shouldHaveValue(refreshResponse)
        
        coVerify { 
            mockTokenManager.updateAccessToken("new_access_token", 3600)
        }
    }

    @Test
    fun `refreshToken should clear tokens on failure`() = runTest {
        // Arrange
        val errorResponse = TestDataFactory.createTestRefreshTokenResponse(false, "Token expired")
        
        coEvery { mockApiService.refreshToken() } returns Response.success(errorResponse)

        // Act
        val result = authRepository.refreshToken()

        // Assert
        result.shouldBeFailure()
        result.shouldHaveError("Session expired")
        
        coVerify { mockTokenManager.clearTokens() }
    }

    @Test
    fun `refreshToken should clear tokens on network error`() = runTest {
        // Arrange
        coEvery { mockApiService.refreshToken() } throws Exception("Network error")

        // Act
        val result = authRepository.refreshToken()

        // Assert
        result.shouldBeFailure()
        coVerify { mockTokenManager.clearTokens() }
    }

    @Test
    fun `logout should call API and clear tokens`() = runTest {
        // Arrange
        coEvery { mockApiService.logout() } returns Response.success(mapOf("success" to true))

        // Act
        val result = authRepository.logout()

        // Assert
        result.shouldBeSuccess()
        
        coVerify { mockApiService.logout() }
        coVerify { mockTokenManager.clearTokens() }
    }

    @Test
    fun `logout should clear tokens even when API call fails`() = runTest {
        // Arrange
        coEvery { mockApiService.logout() } throws Exception("Network error")

        // Act
        val result = authRepository.logout()

        // Assert
        result.shouldBeSuccess() // Should still succeed locally
        coVerify { mockTokenManager.clearTokens() }
    }

    @Test
    fun `getCurrentUserId should return value from TokenManager`() = runTest {
        // Arrange
        coEvery { mockTokenManager.getCurrentUserId() } returns 42

        // Act
        val result = authRepository.getCurrentUserId()

        // Assert
        assert(result == 42)
    }

    @Test
    fun `isLoggedIn should return TokenManager flow`() = runTest {
        // Arrange
        every { mockTokenManager.isLoggedIn } returns flowOf(true)

        // Act
        val result = authRepository.isLoggedIn.first()

        // Assert
        assert(result == true)
    }

    @Test
    fun `formatPhoneNumber should handle various input formats`() = runTest {
        // Test different phone number formats by testing sendOtp
        val testCases = listOf(
            "9876543210" to "+919876543210",
            "+919876543210" to "+919876543210",
            "91 9876543210" to "+919876543210",
            "91-9876-543210" to "+919876543210"
        )
        
        val expectedResponse = TestDataFactory.createTestSendOtpResponse()
        
        testCases.forEach { (input, expected) ->
            // Arrange
            coEvery { mockApiService.sendOtp(any()) } returns Response.success(expectedResponse)
            
            // Act
            authRepository.sendOtp(input)
            
            // Assert
            coVerify { 
                mockApiService.sendOtp(
                    match { request -> request.phoneNumber == expected }
                )
            }
            
            clearMocks(mockApiService)
        }
    }

    @Test
    fun `device ID should fallback to unknown_device on error`() = runTest {
        // Arrange
        every { 
            android.provider.Settings.Secure.getString(any(), any()) 
        } throws SecurityException("Permission denied")
        
        val expectedResponse = TestDataFactory.createTestVerifyOtpResponse()
        coEvery { mockApiService.verifyOtp(any()) } returns Response.success(expectedResponse)

        // Act
        val result = authRepository.verifyOtp("+919876543210", "123456")

        // Assert
        result.shouldBeSuccess()
        coVerify { 
            mockApiService.verifyOtp(
                match { request -> request.deviceId == "unknown_device" }
            )
        }
    }
}