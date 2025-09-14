package com.plstravels.driver.performance

import androidx.benchmark.junit4.BenchmarkRule
import androidx.benchmark.junit4.measureRepeated
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.plstravels.driver.data.local.LocationDao
import com.plstravels.driver.data.local.PLSDatabase
import com.plstravels.driver.testutils.factories.TestDataFactory
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Performance benchmarking tests for critical operations
 * Measures performance of location tracking, database operations, and data processing
 */
@RunWith(AndroidJUnit4::class)
class LocationTrackingPerformanceTest {

    @get:Rule
    val benchmarkRule = BenchmarkRule()

    private lateinit var database: PLSDatabase
    private lateinit var locationDao: LocationDao

    @Before
    fun setup() {
        database = Room.inMemoryDatabaseBuilder(
            ApplicationProvider.getApplicationContext(),
            PLSDatabase::class.java
        ).build()
        
        locationDao = database.locationDao()
    }

    @After
    fun teardown() {
        database.close()
    }

    @Test
    fun benchmarkLocationPointInsertion() {
        val locationPoint = TestDataFactory.createTestLocationPoint(dutyId = 1)
        
        benchmarkRule.measureRepeated {
            runBlocking {
                locationDao.insertLocationPoint(locationPoint)
            }
        }
    }

    @Test
    fun benchmarkBatchLocationInsertion() {
        val locationPoints = TestDataFactory.createTestLocationPointList(dutyId = 1, count = 100)
        
        benchmarkRule.measureRepeated {
            runBlocking {
                locationPoints.forEach { point ->
                    locationDao.insertLocationPoint(point)
                }
            }
        }
    }

    @Test
    fun benchmarkLocationQuery() {
        // Setup test data
        runBlocking {
            val locationPoints = TestDataFactory.createTestLocationPointList(dutyId = 1, count = 1000)
            locationPoints.forEach { point ->
                locationDao.insertLocationPoint(point)
            }
        }

        benchmarkRule.measureRepeated {
            runBlocking {
                locationDao.getLocationPointsByDutyId(1)
            }
        }
    }

    @Test
    fun benchmarkDistanceCalculation() {
        val startLat = 12.9716
        val startLng = 77.5946
        val endLat = 13.0827
        val endLng = 80.2707

        benchmarkRule.measureRepeated {
            calculateDistance(startLat, startLng, endLat, endLng)
        }
    }

    @Test
    fun benchmarkLocationDataProcessing() {
        val rawLocationPoints = TestDataFactory.createTestLocationPointList(dutyId = 1, count = 500)

        benchmarkRule.measureRepeated {
            // Simulate location data processing
            val processedPoints = rawLocationPoints
                .filter { it.accuracy <= 20 } // Filter by accuracy
                .sortedBy { it.timestamp } // Sort by time
                .zipWithNext { current, next -> 
                    // Calculate distances between consecutive points
                    calculateDistance(
                        current.latitude, current.longitude,
                        next.latitude, next.longitude
                    )
                }
                .sum() // Total distance
        }
    }

    @Test
    fun benchmarkLocationSessionManagement() {
        val session = TestDataFactory.createTestLocationSession(dutyId = 1)

        benchmarkRule.measureRepeated {
            runBlocking {
                val sessionId = locationDao.insertLocationSession(session)
                locationDao.endLocationSession(sessionId, System.currentTimeMillis())
            }
        }
    }

    @Test
    fun benchmarkSyncPendingLocationQuery() {
        // Setup test data with mix of synced and unsynced locations
        runBlocking {
            repeat(1000) { index ->
                val locationPoint = TestDataFactory.createTestLocationPoint(
                    dutyId = 1,
                    id = index.toLong()
                ).copy(isSynced = index % 3 == 0) // Every 3rd point is synced
                
                locationDao.insertLocationPoint(locationPoint)
            }
        }

        benchmarkRule.measureRepeated {
            runBlocking {
                locationDao.getSyncPendingLocationPoints()
            }
        }
    }

    @Test
    fun benchmarkLocationDataCleanup() {
        // Setup old location data
        runBlocking {
            val oldTimestamp = System.currentTimeMillis() - 30 * 24 * 60 * 60 * 1000L // 30 days ago
            repeat(1000) { index ->
                val locationPoint = TestDataFactory.createTestLocationPoint(
                    dutyId = 1,
                    id = index.toLong(),
                    timestamp = oldTimestamp
                )
                locationDao.insertLocationPoint(locationPoint)
            }
        }

        val cutoffTime = System.currentTimeMillis() - 7 * 24 * 60 * 60 * 1000L // 7 days ago

        benchmarkRule.measureRepeated {
            runBlocking {
                locationDao.deleteOldLocationPoints(cutoffTime)
            }
        }
    }

    @Test
    fun benchmarkLocationAccuracyFiltering() {
        val locationPoints = TestDataFactory.createTestLocationPointList(dutyId = 1, count = 1000)
            .map { it.copy(accuracy = (1..100).random().toFloat()) } // Random accuracy 1-100m

        benchmarkRule.measureRepeated {
            locationPoints
                .filter { it.accuracy <= 20 } // Good accuracy
                .take(100) // Limit results
        }
    }

    @Test
    fun benchmarkSpeedCalculation() {
        val locationPoints = TestDataFactory.createTestLocationPointList(dutyId = 1, count = 100)
            .sortedBy { it.timestamp }

        benchmarkRule.measureRepeated {
            locationPoints.zipWithNext { current, next ->
                val distance = calculateDistance(
                    current.latitude, current.longitude,
                    next.latitude, next.longitude
                )
                val timeDiff = (next.timestamp - current.timestamp) / 1000.0 // seconds
                if (timeDiff > 0) distance / timeDiff * 3.6 else 0.0 // km/h
            }
        }
    }

    @Test
    fun benchmarkGeoFencing() {
        val locationPoints = TestDataFactory.createTestLocationPointList(dutyId = 1, count = 1000)
        val centerLat = 12.9716
        val centerLng = 77.5946
        val radiusMeters = 1000.0

        benchmarkRule.measureRepeated {
            locationPoints.filter { point ->
                val distance = calculateDistance(
                    point.latitude, point.longitude,
                    centerLat, centerLng
                )
                distance <= radiusMeters
            }
        }
    }

    // Helper function for distance calculation
    private fun calculateDistance(lat1: Double, lng1: Double, lat2: Double, lng2: Double): Double {
        val earthRadius = 6371000.0 // meters
        val dLat = Math.toRadians(lat2 - lat1)
        val dLng = Math.toRadians(lng2 - lng1)
        val a = kotlin.math.sin(dLat / 2) * kotlin.math.sin(dLat / 2) +
                kotlin.math.cos(Math.toRadians(lat1)) * kotlin.math.cos(Math.toRadians(lat2)) *
                kotlin.math.sin(dLng / 2) * kotlin.math.sin(dLng / 2)
        val c = 2 * kotlin.math.atan2(kotlin.math.sqrt(a), kotlin.math.sqrt(1 - a))
        return earthRadius * c
    }
}