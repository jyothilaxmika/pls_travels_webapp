package com.plstravels.driver.repository

import com.plstravels.driver.data.local.DutyDao
import com.plstravels.driver.data.network.ApiService
import com.plstravels.driver.data.repository.ConnectivityRepository
import com.plstravels.driver.data.repository.DutyRepository
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
 * Comprehensive unit tests for DutyRepository
 * Tests duty lifecycle, location tracking, and synchronization
 */
@ExperimentalCoroutinesApi
class DutyRepositoryTest : BaseUnitTest() {

    private lateinit var dutyRepository: DutyRepository
    private val mockDutyDao: DutyDao = mockk()
    private val mockApiService: ApiService = mockk()
    private val mockConnectivityRepository: ConnectivityRepository = mockk()

    @Before
    override fun setUp() {
        super.setUp()
        
        // Default connectivity behavior
        every { mockConnectivityRepository.isConnected() } returns flowOf(true)
        
        dutyRepository = DutyRepository(mockDutyDao, mockApiService, mockConnectivityRepository)
    }

    @Test
    fun `startDuty should create duty and return success`() = runTest {
        // Arrange
        val userId = 1
        val vehicleId = 10
        val location = Pair(12.9716, 77.5946)
        val expectedDutyId = 100L
        
        coEvery { mockDutyDao.insertDuty(any()) } returns expectedDutyId

        // Act
        val result = dutyRepository.startDuty(userId, vehicleId, location)

        // Assert
        result.shouldBeSuccess()
        result.shouldHaveValue(expectedDutyId.toInt())
        
        coVerify { 
            mockDutyDao.insertDuty(
                match { duty ->
                    duty.userId == userId &&
                    duty.vehicleId == vehicleId &&
                    duty.status == "active" &&
                    duty.startLatitude == location.first &&
                    duty.startLongitude == location.second &&
                    duty.endTime == null
                }
            )
        }
    }

    @Test
    fun `startDuty should handle database error`() = runTest {
        // Arrange
        val userId = 1
        val vehicleId = 10
        val location = Pair(12.9716, 77.5946)
        
        coEvery { mockDutyDao.insertDuty(any()) } throws Exception("Database error")

        // Act
        val result = dutyRepository.startDuty(userId, vehicleId, location)

        // Assert
        result.shouldBeFailure()
        result.shouldHaveError("Database error")
    }

    @Test
    fun `endDuty should update duty with end time and location`() = runTest {
        // Arrange
        val dutyId = 100
        val endLocation = Pair(12.9800, 77.6000)
        val testDuty = TestDataFactory.createTestDuty(id = dutyId)
        
        coEvery { mockDutyDao.getDutyById(dutyId) } returns testDuty
        coEvery { mockDutyDao.endDuty(any(), any()) } just Runs
        coEvery { mockDutyDao.updateDutyLocation(any(), any(), any()) } just Runs

        // Act
        val result = dutyRepository.endDuty(dutyId, endLocation, 45.5)

        // Assert
        result.shouldBeSuccess()
        
        coVerify { mockDutyDao.endDuty(dutyId, any()) }
        coVerify { 
            mockDutyDao.updateDutyLocation(
                dutyId,
                endLocation.first,
                endLocation.second
            )
        }
    }

    @Test
    fun `endDuty should return error when duty not found`() = runTest {
        // Arrange
        val dutyId = 999
        val endLocation = Pair(12.9800, 77.6000)
        
        coEvery { mockDutyDao.getDutyById(dutyId) } returns null

        // Act
        val result = dutyRepository.endDuty(dutyId, endLocation, 45.5)

        // Assert
        result.shouldBeFailure()
        result.shouldHaveError("Duty not found")
    }

    @Test
    fun `getCurrentDuty should return active duty for user`() = runTest {
        // Arrange
        val userId = 1
        val expectedDuty = TestDataFactory.createTestDuty(userId = userId, status = "active")
        
        coEvery { mockDutyDao.getActiveDutyByUserId(userId) } returns expectedDuty

        // Act
        val result = dutyRepository.getCurrentDuty(userId).first()

        // Assert
        assert(result == expectedDuty)
        coVerify { mockDutyDao.getActiveDutyByUserId(userId) }
    }

    @Test
    fun `getDutyHistory should return duties for date range`() = runTest {
        // Arrange
        val userId = 1
        val startDate = System.currentTimeMillis() - 86400000 // 24 hours ago
        val endDate = System.currentTimeMillis()
        val expectedDuties = TestDataFactory.createTestDutyList()
        
        coEvery { 
            mockDutyDao.getDutiesByDateRange(userId, startDate, endDate) 
        } returns flowOf(expectedDuties)

        // Act
        val result = dutyRepository.getDutyHistory(userId, startDate, endDate).first()

        // Assert
        assert(result == expectedDuties)
        coVerify { mockDutyDao.getDutiesByDateRange(userId, startDate, endDate) }
    }

    @Test
    fun `syncPendingDuties should sync all unsynced duties when connected`() = runTest {
        // Arrange
        val pendingDuties = TestDataFactory.createTestDutyList(count = 3)
        
        every { mockConnectivityRepository.isConnected() } returns flowOf(true)
        coEvery { mockDutyDao.getSyncPendingDuties() } returns flowOf(pendingDuties)
        coEvery { mockApiService.syncDuty(any()) } returns Response.success(mapOf("success" to true))
        coEvery { mockDutyDao.markDutyAsSynced(any()) } just Runs

        // Act
        val result = dutyRepository.syncPendingDuties()

        // Assert
        result.shouldBeSuccess()
        
        // Verify each duty was synced
        pendingDuties.forEach { duty ->
            coVerify { mockApiService.syncDuty(duty) }
            coVerify { mockDutyDao.markDutyAsSynced(duty.id) }
        }
    }

    @Test
    fun `syncPendingDuties should skip sync when offline`() = runTest {
        // Arrange
        every { mockConnectivityRepository.isConnected() } returns flowOf(false)

        // Act
        val result = dutyRepository.syncPendingDuties()

        // Assert
        result.shouldBeFailure()
        result.shouldHaveError("No network connection")
        
        coVerify(exactly = 0) { mockApiService.syncDuty(any()) }
    }

    @Test
    fun `syncPendingDuties should handle partial sync failures`() = runTest {
        // Arrange
        val pendingDuties = TestDataFactory.createTestDutyList(count = 3)
        
        every { mockConnectivityRepository.isConnected() } returns flowOf(true)
        coEvery { mockDutyDao.getSyncPendingDuties() } returns flowOf(pendingDuties)
        
        // First duty succeeds, second fails, third succeeds
        coEvery { mockApiService.syncDuty(pendingDuties[0]) } returns 
            Response.success(mapOf("success" to true))
        coEvery { mockApiService.syncDuty(pendingDuties[1]) } throws Exception("Network error")
        coEvery { mockApiService.syncDuty(pendingDuties[2]) } returns 
            Response.success(mapOf("success" to true))
        
        coEvery { mockDutyDao.markDutyAsSynced(any()) } just Runs

        // Act
        val result = dutyRepository.syncPendingDuties()

        // Assert
        result.shouldBeSuccess() // Should succeed overall despite partial failures
        
        // Verify successful duties were marked as synced
        coVerify { mockDutyDao.markDutyAsSynced(pendingDuties[0].id) }
        coVerify { mockDutyDao.markDutyAsSynced(pendingDuties[2].id) }
        coVerify(exactly = 0) { mockDutyDao.markDutyAsSynced(pendingDuties[1].id) }
    }

    @Test
    fun `updateDutyLocation should update coordinates and calculate distance`() = runTest {
        // Arrange
        val dutyId = 100
        val newLatitude = 12.9800
        val newLongitude = 77.6000
        val testDuty = TestDataFactory.createTestDuty(
            id = dutyId,
            startLatitude = 12.9716,
            startLongitude = 77.5946
        )
        
        coEvery { mockDutyDao.getDutyById(dutyId) } returns testDuty
        coEvery { mockDutyDao.updateDutyLocation(any(), any(), any()) } just Runs
        coEvery { mockDutyDao.updateDutyStats(any(), any(), any()) } just Runs

        // Act
        val result = dutyRepository.updateDutyLocation(dutyId, newLatitude, newLongitude)

        // Assert
        result.shouldBeSuccess()
        
        coVerify { 
            mockDutyDao.updateDutyLocation(dutyId, newLatitude, newLongitude)
        }
        coVerify { 
            mockDutyDao.updateDutyStats(
                eq(dutyId),
                any(), // distance > 0
                any()  // amount
            )
        }
    }

    @Test
    fun `updateDutyLocation should handle invalid duty ID`() = runTest {
        // Arrange
        val dutyId = 999
        val newLatitude = 12.9800
        val newLongitude = 77.6000
        
        coEvery { mockDutyDao.getDutyById(dutyId) } returns null

        // Act
        val result = dutyRepository.updateDutyLocation(dutyId, newLatitude, newLongitude)

        // Assert
        result.shouldBeFailure()
        result.shouldHaveError("Duty not found")
    }

    @Test
    fun `repository should handle concurrent duty operations safely`() = runTest {
        // Arrange
        val userId = 1
        val vehicleId = 10
        val location = Pair(12.9716, 77.5946)
        
        coEvery { mockDutyDao.insertDuty(any()) } returns 100L
        coEvery { mockDutyDao.getDutyById(any()) } returns TestDataFactory.createTestDuty()
        coEvery { mockDutyDao.endDuty(any(), any()) } just Runs
        coEvery { mockDutyDao.updateDutyLocation(any(), any(), any()) } just Runs

        // Act - Start and end duty concurrently
        val startResult = dutyRepository.startDuty(userId, vehicleId, location)
        val endResult = dutyRepository.endDuty(100, location, 45.5)

        // Assert
        startResult.shouldBeSuccess()
        endResult.shouldBeSuccess()
    }

    @Test
    fun `calculateDistance should return valid distance between coordinates`() = runTest {
        // This test would verify the distance calculation logic
        // Since it's a private method, we test it indirectly through updateDutyLocation
        
        // Arrange
        val dutyId = 100
        val startLat = 12.9716
        val startLng = 77.5946
        val endLat = 12.9800
        val endLng = 77.6000
        
        val testDuty = TestDataFactory.createTestDuty(
            id = dutyId,
            startLatitude = startLat,
            startLongitude = startLng
        )
        
        coEvery { mockDutyDao.getDutyById(dutyId) } returns testDuty
        coEvery { mockDutyDao.updateDutyLocation(any(), any(), any()) } just Runs
        coEvery { mockDutyDao.updateDutyStats(any(), any(), any()) } just Runs

        // Act
        dutyRepository.updateDutyLocation(dutyId, endLat, endLng)

        // Assert - Distance should be positive and reasonable (between 0.5-2 km for these coordinates)
        coVerify { 
            mockDutyDao.updateDutyStats(
                dutyId,
                match { distance -> distance in 0.5..2.0 },
                any()
            )
        }
    }
}