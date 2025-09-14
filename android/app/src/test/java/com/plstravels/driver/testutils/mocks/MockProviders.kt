package com.plstravels.driver.testutils.mocks

import com.plstravels.driver.data.local.*
import com.plstravels.driver.data.network.ApiService
import com.plstravels.driver.data.network.RefreshApiService
import com.plstravels.driver.data.repository.*
import com.plstravels.driver.testutils.factories.TestDataFactory
import io.mockk.*
import kotlinx.coroutines.flow.flowOf
import okhttp3.ResponseBody.Companion.toResponseBody
import retrofit2.Response

/**
 * Centralized mock providers for all test dependencies
 * Provides consistent mock configurations across test classes
 */
object MockProviders {

    // DAO Mocks
    fun createMockUserDao(): UserDao = mockk {
        coEvery { insertUser(any()) } returns 1L
        coEvery { getUserById(any()) } returns TestDataFactory.createTestUser()
        coEvery { getUserByPhoneNumber(any()) } returns TestDataFactory.createTestUser()
        coEvery { updateUser(any()) } returns Unit
        coEvery { deleteUser(any()) } returns Unit
        coEvery { getAllUsers() } returns flowOf(listOf(TestDataFactory.createTestUser()))
    }

    fun createMockDutyDao(): DutyDao = mockk {
        coEvery { insertDuty(any()) } returns 1L
        coEvery { getDutyById(any()) } returns TestDataFactory.createTestDuty()
        coEvery { getDutiesByUserId(any()) } returns flowOf(TestDataFactory.createTestDutyList())
        coEvery { getActiveDutyByUserId(any()) } returns TestDataFactory.createTestDuty()
        coEvery { updateDuty(any()) } returns Unit
        coEvery { endDuty(any(), any()) } returns Unit
        coEvery { updateDutyLocation(any(), any(), any()) } returns Unit
        coEvery { updateDutyStats(any(), any(), any()) } returns Unit
        coEvery { getDutiesByDateRange(any(), any(), any()) } returns flowOf(TestDataFactory.createTestDutyList())
        coEvery { getSyncPendingDuties() } returns flowOf(TestDataFactory.createTestDutyList())
        coEvery { markDutyAsSynced(any()) } returns Unit
    }

    fun createMockLocationDao(): LocationDao = mockk {
        coEvery { insertLocationPoint(any()) } returns 1L
        coEvery { insertLocationSession(any()) } returns 1L
        coEvery { getLocationPointsByDutyId(any()) } returns flowOf(TestDataFactory.createTestLocationPointList(1))
        coEvery { getLocationSession(any()) } returns TestDataFactory.createTestLocationSession()
        coEvery { endLocationSession(any(), any()) } returns Unit
        coEvery { updateLocationSessionStats(any(), any(), any()) } returns Unit
        coEvery { getSyncPendingLocationPoints() } returns flowOf(TestDataFactory.createTestLocationPointList(1))
        coEvery { markLocationPointAsSynced(any()) } returns Unit
        coEvery { deleteOldLocationPoints(any()) } returns 5
    }

    fun createMockPhotoDao(): PhotoDao = mockk {
        coEvery { insertPhoto(any()) } returns 1L
        coEvery { getPhotoById(any()) } returns TestDataFactory.createTestPhoto()
        coEvery { getPhotosByDutyId(any()) } returns flowOf(TestDataFactory.createTestPhotoList(1))
        coEvery { getPhotosByUserId(any()) } returns flowOf(TestDataFactory.createTestPhotoList(1))
        coEvery { updatePhoto(any()) } returns Unit
        coEvery { deletePhoto(any()) } returns Unit
        coEvery { getSyncPendingPhotos() } returns flowOf(TestDataFactory.createTestPhotoList(1))
        coEvery { markPhotoAsSynced(any(), any()) } returns Unit
        coEvery { getPhotosByType(any(), any()) } returns flowOf(TestDataFactory.createTestPhotoList(1))
    }

    fun createMockNotificationDao(): NotificationDao = mockk {
        coEvery { insertNotification(any()) } returns 1L
        coEvery { getNotificationById(any()) } returns TestDataFactory.createTestNotification()
        coEvery { getNotificationsByUserId(any()) } returns flowOf(TestDataFactory.createTestNotificationList(1))
        coEvery { markNotificationAsRead(any()) } returns Unit
        coEvery { deleteNotification(any()) } returns Unit
        coEvery { getUnreadNotifications(any()) } returns flowOf(TestDataFactory.createTestNotificationList(1))
        coEvery { deleteOldNotifications(any()) } returns 10
    }

    fun createMockCommandQueueDao(): CommandQueueDao = mockk {
        coEvery { insertCommand(any()) } returns 1L
        coEvery { getCommandById(any()) } returns TestDataFactory.createTestCommand()
        coEvery { getPendingCommands() } returns flowOf(listOf(TestDataFactory.createTestCommand()))
        coEvery { updateCommand(any()) } returns Unit
        coEvery { deleteCommand(any()) } returns Unit
        coEvery { markCommandAsCompleted(any(), any()) } returns Unit
        coEvery { markCommandAsFailed(any(), any()) } returns Unit
        coEvery { incrementRetryCount(any()) } returns Unit
        coEvery { getScheduledCommands(any()) } returns flowOf(listOf(TestDataFactory.createTestCommand()))
    }

    fun createMockTokenManager(): TokenManager = mockk {
        coEvery { saveTokens(any(), any(), any(), any(), any(), any()) } returns Unit
        coEvery { getAccessToken() } returns "test_access_token"
        coEvery { getRefreshToken() } returns "test_refresh_token"
        coEvery { getCurrentUserId() } returns 1
        coEvery { getCurrentUsername() } returns "test_user"
        coEvery { getCurrentUserRole() } returns "driver"
        coEvery { updateAccessToken(any(), any()) } returns Unit
        coEvery { clearTokens() } returns Unit
        coEvery { isTokenExpired() } returns false
        every { isLoggedIn } returns flowOf(true)
    }

    // API Service Mocks
    fun createMockApiService(): ApiService = mockk {
        coEvery { sendOtp(any()) } returns Response.success(TestDataFactory.createTestSendOtpResponse())
        coEvery { verifyOtp(any()) } returns Response.success(TestDataFactory.createTestVerifyOtpResponse())
        coEvery { logout() } returns Response.success(mapOf("success" to true))
        coEvery { syncDuty(any()) } returns Response.success(mapOf("success" to true))
        coEvery { syncLocation(any()) } returns Response.success(mapOf("success" to true))
        coEvery { uploadPhoto(any(), any()) } returns Response.success(mapOf("success" to true, "url" to "https://test.com/photo.jpg"))
        coEvery { getDuties(any(), any()) } returns Response.success(TestDataFactory.createTestDutyList())
        coEvery { getNotifications(any()) } returns Response.success(TestDataFactory.createTestNotificationList(1))
    }

    fun createMockRefreshApiService(): RefreshApiService = mockk {
        coEvery { refreshToken() } returns Response.success(TestDataFactory.createTestRefreshTokenResponse())
    }

    // Repository Mocks
    fun createMockAuthRepository(): AuthRepository = mockk {
        coEvery { sendOtp(any()) } returns Result.success(TestDataFactory.createTestSendOtpResponse())
        coEvery { verifyOtp(any(), any()) } returns Result.success(TestDataFactory.createTestVerifyOtpResponse())
        coEvery { refreshToken() } returns Result.success(TestDataFactory.createTestRefreshTokenResponse())
        coEvery { logout() } returns Result.success(Unit)
        coEvery { getCurrentUserId() } returns 1
        coEvery { getCurrentUsername() } returns "test_user"
        coEvery { getCurrentUserRole() } returns "driver"
        every { isLoggedIn } returns flowOf(true)
    }

    fun createMockDutyRepository(): DutyRepository = mockk {
        coEvery { startDuty(any(), any(), any()) } returns Result.success(1)
        coEvery { endDuty(any(), any(), any()) } returns Result.success(Unit)
        coEvery { getCurrentDuty(any()) } returns flowOf(TestDataFactory.createTestDuty())
        coEvery { getDutyHistory(any()) } returns flowOf(TestDataFactory.createTestDutyList())
        coEvery { syncPendingDuties() } returns Result.success(Unit)
        coEvery { updateDutyLocation(any(), any(), any()) } returns Result.success(Unit)
    }

    fun createMockLocationRepository(): LocationRepository = mockk {
        coEvery { startLocationTracking(any()) } returns Result.success(1L)
        coEvery { stopLocationTracking(any()) } returns Result.success(Unit)
        coEvery { saveLocationPoint(any()) } returns Result.success(1L)
        coEvery { getLocationPoints(any()) } returns flowOf(TestDataFactory.createTestLocationPointList(1))
        coEvery { syncPendingLocationData() } returns Result.success(Unit)
        coEvery { cleanupOldLocationData() } returns Result.success(5)
    }

    fun createMockPhotoRepository(): PhotoRepository = mockk {
        coEvery { savePhoto(any()) } returns Result.success(1L)
        coEvery { uploadPhoto(any()) } returns Result.success("https://test.com/photo.jpg")
        coEvery { getPhotosByDuty(any()) } returns flowOf(TestDataFactory.createTestPhotoList(1))
        coEvery { syncPendingPhotos() } returns Result.success(Unit)
        coEvery { deletePhoto(any()) } returns Result.success(Unit)
    }

    fun createMockNotificationRepository(): NotificationRepository = mockk {
        coEvery { saveNotification(any()) } returns Result.success(1L)
        coEvery { getNotifications(any()) } returns flowOf(TestDataFactory.createTestNotificationList(1))
        coEvery { markAsRead(any()) } returns Result.success(Unit)
        coEvery { deleteNotification(any()) } returns Result.success(Unit)
        coEvery { getUnreadCount(any()) } returns flowOf(5)
    }

    fun createMockCommandQueueRepository(): CommandQueueRepository = mockk {
        coEvery { enqueueCommand(any()) } returns Result.success(1L)
        coEvery { processCommands() } returns Result.success(Unit)
        coEvery { getScheduledCommands() } returns flowOf(listOf(TestDataFactory.createTestCommand()))
        coEvery { retryFailedCommands() } returns Result.success(Unit)
    }

    fun createMockConnectivityRepository(): ConnectivityRepository = mockk {
        every { isConnected() } returns flowOf(true)
        every { isWifiConnected() } returns flowOf(false)
        every { isMobileConnected() } returns flowOf(true)
        every { getConnectionType() } returns flowOf("mobile")
        coEvery { waitForConnection() } returns Unit
    }

    // Error Response Mocks
    fun createErrorResponse(code: Int = 500, message: String = "Internal Server Error"): Response<Any> {
        return Response.error(code, message.toResponseBody())
    }

    fun createNetworkErrorResponse(): Response<Any> {
        return Response.error(503, "Service Unavailable".toResponseBody())
    }

    fun createAuthErrorResponse(): Response<Any> {
        return Response.error(401, "Unauthorized".toResponseBody())
    }

    // Database Mock
    fun createMockDatabase(): PLSDatabase = mockk {
        every { userDao() } returns createMockUserDao()
        every { dutyDao() } returns createMockDutyDao()
        every { locationDao() } returns createMockLocationDao()
        every { photoDao() } returns createMockPhotoDao()
        every { notificationDao() } returns createMockNotificationDao()
        every { commandQueueDao() } returns createMockCommandQueueDao()
    }

    // Mock configurations for different test scenarios
    fun configureMocksForOfflineScenario() {
        // Configure mocks to simulate offline behavior
        // Network calls should fail, but local operations should succeed
    }

    fun configureMocksForSyncScenario() {
        // Configure mocks to simulate data synchronization
        // Some data marked as not synced, sync operations succeed
    }

    fun configureMocksForErrorScenario() {
        // Configure mocks to simulate various error conditions
        // Network failures, database errors, authentication errors
    }

    // Helper function to reset all mocks
    fun resetAllMocks() {
        clearAllMocks()
    }
}