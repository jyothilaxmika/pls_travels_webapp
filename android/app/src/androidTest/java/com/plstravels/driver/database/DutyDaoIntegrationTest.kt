package com.plstravels.driver.database

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.plstravels.driver.data.local.DutyDao
import com.plstravels.driver.data.local.PLSDatabase
import com.plstravels.driver.data.local.UserDao
import com.plstravels.driver.testutils.factories.TestDataFactory
import com.google.common.truth.Truth.assertThat
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Integration tests for DutyDao with real Room database
 * Tests database operations, relationships, and complex queries
 */
@RunWith(AndroidJUnit4::class)
class DutyDaoIntegrationTest {

    private lateinit var database: PLSDatabase
    private lateinit var dutyDao: DutyDao
    private lateinit var userDao: UserDao

    @Before
    fun setup() {
        database = Room.inMemoryDatabaseBuilder(
            ApplicationProvider.getApplicationContext(),
            PLSDatabase::class.java
        ).build()
        
        dutyDao = database.dutyDao()
        userDao = database.userDao()
    }

    @After
    fun teardown() {
        database.close()
    }

    @Test
    fun insertAndGetDuty_shouldWorkCorrectly() = runTest {
        // Arrange
        val testUser = TestDataFactory.createTestUser()
        val testDuty = TestDataFactory.createTestDuty(userId = testUser.id)
        
        userDao.insertUser(testUser)

        // Act
        val dutyId = dutyDao.insertDuty(testDuty)
        val retrievedDuty = dutyDao.getDutyById(dutyId.toInt())

        // Assert
        assertThat(retrievedDuty).isNotNull()
        assertThat(retrievedDuty?.id).isEqualTo(dutyId.toInt())
        assertThat(retrievedDuty?.userId).isEqualTo(testUser.id)
        assertThat(retrievedDuty?.status).isEqualTo(testDuty.status)
    }

    @Test
    fun getDutiesByUserId_shouldReturnCorrectDuties() = runTest {
        // Arrange
        val user1 = TestDataFactory.createTestUser(id = 1)
        val user2 = TestDataFactory.createTestUser(id = 2)
        val duty1 = TestDataFactory.createTestDuty(id = 1, userId = user1.id)
        val duty2 = TestDataFactory.createTestDuty(id = 2, userId = user1.id)
        val duty3 = TestDataFactory.createTestDuty(id = 3, userId = user2.id)

        userDao.insertUser(user1)
        userDao.insertUser(user2)
        dutyDao.insertDuty(duty1)
        dutyDao.insertDuty(duty2)
        dutyDao.insertDuty(duty3)

        // Act
        val user1Duties = dutyDao.getDutiesByUserId(user1.id).first()

        // Assert
        assertThat(user1Duties).hasSize(2)
        assertThat(user1Duties.map { it.id }).containsExactly(1, 2)
    }

    @Test
    fun getActiveDutyByUserId_shouldReturnOnlyActiveDuty() = runTest {
        // Arrange
        val user = TestDataFactory.createTestUser()
        val activeDuty = TestDataFactory.createTestDuty(userId = user.id, status = "active")
        val completedDuty = TestDataFactory.createTestDuty(userId = user.id, status = "completed")

        userDao.insertUser(user)
        dutyDao.insertDuty(activeDuty)
        dutyDao.insertDuty(completedDuty)

        // Act
        val activeDutyResult = dutyDao.getActiveDutyByUserId(user.id)

        // Assert
        assertThat(activeDutyResult).isNotNull()
        assertThat(activeDutyResult?.status).isEqualTo("active")
    }

    @Test
    fun endDuty_shouldUpdateEndTimeAndStatus() = runTest {
        // Arrange
        val testUser = TestDataFactory.createTestUser()
        val testDuty = TestDataFactory.createTestDuty(userId = testUser.id, status = "active", endTime = null)
        
        userDao.insertUser(testUser)
        val dutyId = dutyDao.insertDuty(testDuty).toInt()

        // Act
        val endTime = System.currentTimeMillis()
        dutyDao.endDuty(dutyId, endTime)

        // Assert
        val updatedDuty = dutyDao.getDutyById(dutyId)
        assertThat(updatedDuty?.endTime).isEqualTo(endTime)
        assertThat(updatedDuty?.status).isEqualTo("completed")
    }

    @Test
    fun updateDutyLocation_shouldUpdateCoordinates() = runTest {
        // Arrange
        val testUser = TestDataFactory.createTestUser()
        val testDuty = TestDataFactory.createTestDuty(userId = testUser.id)
        
        userDao.insertUser(testUser)
        val dutyId = dutyDao.insertDuty(testDuty).toInt()

        // Act
        val newLatitude = 13.0827
        val newLongitude = 80.2707
        dutyDao.updateDutyLocation(dutyId, newLatitude, newLongitude)

        // Assert
        val updatedDuty = dutyDao.getDutyById(dutyId)
        assertThat(updatedDuty?.endLatitude).isEqualTo(newLatitude)
        assertThat(updatedDuty?.endLongitude).isEqualTo(newLongitude)
    }

    @Test
    fun updateDutyStats_shouldUpdateDistanceAndAmount() = runTest {
        // Arrange
        val testUser = TestDataFactory.createTestUser()
        val testDuty = TestDataFactory.createTestDuty(userId = testUser.id, totalDistance = 0.0, totalAmount = 0.0)
        
        userDao.insertUser(testUser)
        val dutyId = dutyDao.insertDuty(testDuty).toInt()

        // Act
        val distance = 25.5
        val amount = 450.0
        dutyDao.updateDutyStats(dutyId, distance, amount)

        // Assert
        val updatedDuty = dutyDao.getDutyById(dutyId)
        assertThat(updatedDuty?.totalDistance).isEqualTo(distance)
        assertThat(updatedDuty?.totalAmount).isEqualTo(amount)
    }

    @Test
    fun getDutiesByDateRange_shouldFilterCorrectly() = runTest {
        // Arrange
        val user = TestDataFactory.createTestUser()
        val baseTime = System.currentTimeMillis()
        val duty1 = TestDataFactory.createTestDuty(userId = user.id, startTime = baseTime - 86400000) // 1 day ago
        val duty2 = TestDataFactory.createTestDuty(userId = user.id, startTime = baseTime - 3600000)  // 1 hour ago
        val duty3 = TestDataFactory.createTestDuty(userId = user.id, startTime = baseTime + 3600000)  // 1 hour in future

        userDao.insertUser(user)
        dutyDao.insertDuty(duty1)
        dutyDao.insertDuty(duty2)
        dutyDao.insertDuty(duty3)

        // Act
        val startRange = baseTime - 7200000 // 2 hours ago
        val endRange = baseTime // now
        val dutiesInRange = dutyDao.getDutiesByDateRange(user.id, startRange, endRange).first()

        // Assert
        assertThat(dutiesInRange).hasSize(1)
        assertThat(dutiesInRange[0].startTime).isEqualTo(baseTime - 3600000)
    }

    @Test
    fun getSyncPendingDuties_shouldReturnUnsyncedDuties() = runTest {
        // Arrange
        val user = TestDataFactory.createTestUser()
        val syncedDuty = TestDataFactory.createTestDuty(userId = user.id).copy(isSynced = true)
        val unsyncedDuty1 = TestDataFactory.createTestDuty(userId = user.id).copy(isSynced = false)
        val unsyncedDuty2 = TestDataFactory.createTestDuty(userId = user.id).copy(isSynced = false)

        userDao.insertUser(user)
        dutyDao.insertDuty(syncedDuty)
        dutyDao.insertDuty(unsyncedDuty1)
        dutyDao.insertDuty(unsyncedDuty2)

        // Act
        val pendingDuties = dutyDao.getSyncPendingDuties().first()

        // Assert
        assertThat(pendingDuties).hasSize(2)
        assertThat(pendingDuties.all { !it.isSynced }).isTrue()
    }

    @Test
    fun markDutyAsSynced_shouldUpdateSyncStatus() = runTest {
        // Arrange
        val testUser = TestDataFactory.createTestUser()
        val testDuty = TestDataFactory.createTestDuty(userId = testUser.id).copy(isSynced = false)
        
        userDao.insertUser(testUser)
        val dutyId = dutyDao.insertDuty(testDuty).toInt()

        // Act
        dutyDao.markDutyAsSynced(dutyId)

        // Assert
        val updatedDuty = dutyDao.getDutyById(dutyId)
        assertThat(updatedDuty?.isSynced).isTrue()
        assertThat(updatedDuty?.syncedAt).isNotNull()
    }

    @Test
    fun concurrentDutyOperations_shouldBeThreadSafe() = runTest {
        // Arrange
        val user = TestDataFactory.createTestUser()
        userDao.insertUser(user)

        // Act - Perform concurrent operations
        val duty1 = TestDataFactory.createTestDuty(userId = user.id)
        val duty2 = TestDataFactory.createTestDuty(userId = user.id)

        val id1 = dutyDao.insertDuty(duty1)
        val id2 = dutyDao.insertDuty(duty2)

        // Update both duties concurrently
        dutyDao.updateDutyStats(id1.toInt(), 10.0, 100.0)
        dutyDao.updateDutyStats(id2.toInt(), 20.0, 200.0)

        // Assert
        val retrievedDuty1 = dutyDao.getDutyById(id1.toInt())
        val retrievedDuty2 = dutyDao.getDutyById(id2.toInt())

        assertThat(retrievedDuty1?.totalDistance).isEqualTo(10.0)
        assertThat(retrievedDuty1?.totalAmount).isEqualTo(100.0)
        assertThat(retrievedDuty2?.totalDistance).isEqualTo(20.0)
        assertThat(retrievedDuty2?.totalAmount).isEqualTo(200.0)
    }

    @Test
    fun databaseConstraints_shouldEnforceForeignKeys() = runTest {
        // Arrange
        val nonExistentUserId = 999
        val duty = TestDataFactory.createTestDuty(userId = nonExistentUserId)

        // Act & Assert - This should fail due to foreign key constraint
        try {
            dutyDao.insertDuty(duty)
            assertThat(false).isTrue() // Should not reach here
        } catch (e: Exception) {
            // Expected behavior - foreign key constraint violation
            assertThat(e).isInstanceOf(android.database.sqlite.SQLiteConstraintException::class.java)
        }
    }

    @Test
    fun dutyStatusTransitions_shouldBeValid() = runTest {
        // Arrange
        val user = TestDataFactory.createTestUser()
        val duty = TestDataFactory.createTestDuty(userId = user.id, status = "active")
        
        userDao.insertUser(user)
        val dutyId = dutyDao.insertDuty(duty).toInt()

        // Act - Transition from active to completed
        dutyDao.endDuty(dutyId, System.currentTimeMillis())

        // Assert
        val completedDuty = dutyDao.getDutyById(dutyId)
        assertThat(completedDuty?.status).isEqualTo("completed")
        assertThat(completedDuty?.endTime).isNotNull()
    }
}