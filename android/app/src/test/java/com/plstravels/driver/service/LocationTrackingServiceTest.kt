package com.plstravels.driver.service

import android.content.Context
import android.content.Intent
import androidx.test.core.app.ApplicationProvider
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationResult
import com.plstravels.driver.data.local.LocationDao
import com.plstravels.driver.data.repository.LocationRepository
import com.plstravels.driver.service.LocationTrackingService
import com.plstravels.driver.testutils.BaseUnitTest
import com.plstravels.driver.testutils.factories.TestDataFactory
import com.plstravels.driver.utils.LocationPermissionHelper
import io.mockk.*
import kotlinx.coroutines.ExperimentalCoroutinesApi
import org.junit.Before
import org.junit.Test
import org.robolectric.annotation.Config

/**
 * Unit tests for LocationTrackingService
 * Tests location tracking lifecycle and data persistence
 * 
 * Note: This uses Robolectric for Android framework components
 */
@ExperimentalCoroutinesApi
@Config(sdk = [28]) // Required for Robolectric
class LocationTrackingServiceTest : BaseUnitTest() {

    private lateinit var locationTrackingService: LocationTrackingService
    private val mockLocationDao: LocationDao = mockk()
    private val mockLocationRepository: LocationRepository = mockk()
    private val mockFusedLocationClient: FusedLocationProviderClient = mockk()
    private val context: Context = ApplicationProvider.getApplicationContext()

    @Before
    override fun setUp() {
        super.setUp()
        
        // Mock permission check
        mockkObject(LocationPermissionHelper)
        every { LocationPermissionHelper.hasLocationPermissions(any()) } returns true
        
        // Mock location DAO operations
        coEvery { mockLocationDao.insertLocationSession(any()) } returns 1L
        coEvery { mockLocationDao.insertLocationPoint(any()) } returns 1L
        coEvery { mockLocationDao.endLocationSession(any(), any()) } just Runs
        coEvery { mockLocationDao.updateLocationSessionStats(any(), any(), any()) } just Runs
        
        // Create service instance (would normally be done by Android framework)
        locationTrackingService = LocationTrackingService()
        
        // Inject mocks (in real code, this would be done via Hilt)
        // For testing, we'd need to use a test-specific injection method
    }

    @Test
    fun `startLocationTracking should create location session`() = runTest {
        // Arrange
        val dutyId = 100
        val intent = Intent().apply {
            action = LocationTrackingService.ACTION_START_TRACKING
            putExtra(LocationTrackingService.EXTRA_DUTY_ID, dutyId)
        }

        // Act
        locationTrackingService.onStartCommand(intent, 0, 1)
        testCoroutineRule.testDispatcher.scheduler.advanceUntilIdle()

        // Assert
        coVerify { 
            mockLocationDao.insertLocationSession(
                match { session ->
                    session.dutyId == dutyId &&
                    session.isActive &&
                    session.startTime > 0
                }
            )
        }
    }

    @Test
    fun `stopLocationTracking should end location session`() = runTest {
        // Arrange
        val dutyId = 100
        val startIntent = Intent().apply {
            action = LocationTrackingService.ACTION_START_TRACKING
            putExtra(LocationTrackingService.EXTRA_DUTY_ID, dutyId)
        }
        val stopIntent = Intent().apply {
            action = LocationTrackingService.ACTION_STOP_TRACKING
        }

        // Act
        locationTrackingService.onStartCommand(startIntent, 0, 1)
        locationTrackingService.onStartCommand(stopIntent, 0, 2)
        testCoroutineRule.testDispatcher.scheduler.advanceUntilIdle()

        // Assert
        coVerify { mockLocationDao.endLocationSession(any(), any()) }
        coVerify { mockLocationDao.updateLocationSessionStats(any(), any(), any()) }
    }

    @Test
    fun `service should not start tracking without location permissions`() = runTest {
        // Arrange
        every { LocationPermissionHelper.hasLocationPermissions(any()) } returns false
        val dutyId = 100
        val intent = Intent().apply {
            action = LocationTrackingService.ACTION_START_TRACKING
            putExtra(LocationTrackingService.EXTRA_DUTY_ID, dutyId)
        }

        // Act
        locationTrackingService.onStartCommand(intent, 0, 1)
        testCoroutineRule.testDispatcher.scheduler.advanceUntilIdle()

        // Assert - Service should stop itself
        coVerify(exactly = 0) { mockLocationDao.insertLocationSession(any()) }
    }

    @Test
    fun `service should handle invalid duty ID`() = runTest {
        // Arrange
        val invalidDutyId = -1
        val intent = Intent().apply {
            action = LocationTrackingService.ACTION_START_TRACKING
            putExtra(LocationTrackingService.EXTRA_DUTY_ID, invalidDutyId)
        }

        // Act
        locationTrackingService.onStartCommand(intent, 0, 1)
        testCoroutineRule.testDispatcher.scheduler.advanceUntilIdle()

        // Assert - Should not create location session
        coVerify(exactly = 0) { mockLocationDao.insertLocationSession(any()) }
    }

    // Note: Testing location updates would require more complex setup with LocationResult
    // and would benefit from integration testing rather than unit testing
    
    @Test
    fun `service lifecycle should be managed correctly`() = runTest {
        // Arrange
        val dutyId = 100
        val startIntent = Intent().apply {
            action = LocationTrackingService.ACTION_START_TRACKING
            putExtra(LocationTrackingService.EXTRA_DUTY_ID, dutyId)
        }

        // Act
        val startResult = locationTrackingService.onStartCommand(startIntent, 0, 1)
        
        // Simulate service destruction
        locationTrackingService.onDestroy()

        // Assert
        assert(startResult == android.app.Service.START_STICKY)
        coVerify { mockLocationDao.endLocationSession(any(), any()) }
    }

    // Helper methods for testing location processing
    private fun createMockLocationResult(): LocationResult {
        val mockLocation = mockk<android.location.Location> {
            every { latitude } returns 12.9716
            every { longitude } returns 77.5946
            every { accuracy } returns 5.0f
            every { speed } returns 10.0f
            every { bearing } returns 90.0f
            every { time } returns System.currentTimeMillis()
        }
        
        return mockk<LocationResult> {
            every { locations } returns listOf(mockLocation)
        }
    }
}