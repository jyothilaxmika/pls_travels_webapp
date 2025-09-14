package com.plstravels.driver.testutils.factories

import com.plstravels.driver.data.models.*
import java.util.*
import kotlin.random.Random

/**
 * Factory for creating test data objects with realistic values
 * Provides consistent test data across all test classes
 */
object TestDataFactory {

    // User Test Data
    fun createTestUser(
        id: Int = Random.nextInt(1, 1000),
        username: String = "test_user_$id",
        phoneNumber: String = "+919876543210",
        role: String = "driver",
        isActive: Boolean = true
    ) = User(
        id = id,
        username = username,
        phoneNumber = phoneNumber,
        role = role,
        isActive = isActive,
        createdAt = System.currentTimeMillis() - Random.nextLong(0, 86400000), // Random time within last 24 hours
        updatedAt = System.currentTimeMillis()
    )

    // Duty Test Data
    fun createTestDuty(
        id: Int = Random.nextInt(1, 1000),
        userId: Int = Random.nextInt(1, 100),
        vehicleId: Int = Random.nextInt(1, 50),
        status: String = "active",
        startTime: Long = System.currentTimeMillis() - Random.nextLong(0, 7200000), // Started within last 2 hours
        endTime: Long? = null,
        startLatitude: Double = 12.9716 + Random.nextDouble(-0.1, 0.1), // Bangalore vicinity
        startLongitude: Double = 77.5946 + Random.nextDouble(-0.1, 0.1),
        endLatitude: Double? = null,
        endLongitude: Double? = null,
        totalDistance: Double = 0.0,
        totalAmount: Double = 0.0
    ) = Duty(
        id = id,
        userId = userId,
        vehicleId = vehicleId,
        status = status,
        startTime = startTime,
        endTime = endTime,
        startLatitude = startLatitude,
        startLongitude = startLongitude,
        endLatitude = endLatitude,
        endLongitude = endLongitude,
        totalDistance = totalDistance,
        totalAmount = totalAmount,
        createdAt = startTime,
        updatedAt = System.currentTimeMillis()
    )

    // Location Test Data
    fun createTestLocationPoint(
        id: Long = Random.nextLong(1, 10000),
        dutyId: Int = Random.nextInt(1, 1000),
        latitude: Double = 12.9716 + Random.nextDouble(-0.1, 0.1),
        longitude: Double = 77.5946 + Random.nextDouble(-0.1, 0.1),
        accuracy: Float = Random.nextFloat() * 10 + 3, // 3-13 meters
        speed: Float = Random.nextFloat() * 60, // 0-60 km/h
        bearing: Float = Random.nextFloat() * 360,
        timestamp: Long = System.currentTimeMillis() - Random.nextLong(0, 3600000) // Within last hour
    ) = LocationPoint(
        id = id,
        dutyId = dutyId,
        latitude = latitude,
        longitude = longitude,
        accuracy = accuracy,
        speed = speed,
        bearing = bearing,
        timestamp = timestamp,
        isSynced = Random.nextBoolean()
    )

    fun createTestLocationSession(
        id: Long = Random.nextLong(1, 1000),
        dutyId: Int = Random.nextInt(1, 1000),
        startTime: Long = System.currentTimeMillis() - Random.nextLong(0, 7200000),
        endTime: Long? = null,
        isActive: Boolean = true,
        pointCount: Int = Random.nextInt(0, 100),
        totalDistance: Double = Random.nextDouble(0.0, 50.0),
        averageSpeed: Double = Random.nextDouble(20.0, 60.0)
    ) = LocationSession(
        id = id,
        dutyId = dutyId,
        startTime = startTime,
        endTime = endTime,
        isActive = isActive,
        pointCount = pointCount,
        totalDistance = totalDistance,
        averageSpeed = averageSpeed
    )

    // Photo Test Data
    fun createTestPhoto(
        id: Long = Random.nextLong(1, 10000),
        dutyId: Int = Random.nextInt(1, 1000),
        userId: Int = Random.nextInt(1, 100),
        photoType: String = "duty_start",
        fileName: String = "test_photo_${System.currentTimeMillis()}.jpg",
        filePath: String = "/storage/test/$fileName",
        fileSize: Long = Random.nextLong(1024, 5242880), // 1KB to 5MB
        mimeType: String = "image/jpeg",
        capturedAt: Long = System.currentTimeMillis() - Random.nextLong(0, 3600000),
        isSynced: Boolean = Random.nextBoolean(),
        latitude: Double? = 12.9716 + Random.nextDouble(-0.1, 0.1),
        longitude: Double? = 77.5946 + Random.nextDouble(-0.1, 0.1)
    ) = Photo(
        id = id,
        dutyId = dutyId,
        userId = userId,
        photoType = photoType,
        fileName = fileName,
        filePath = filePath,
        fileSize = fileSize,
        mimeType = mimeType,
        capturedAt = capturedAt,
        uploadedAt = if (isSynced) capturedAt + Random.nextLong(1000, 60000) else null,
        isSynced = isSynced,
        latitude = latitude,
        longitude = longitude,
        metadata = createPhotoMetadata()
    )

    private fun createPhotoMetadata(): String {
        return """
            {
                "device_model": "Test Device",
                "device_brand": "TestBrand",
                "app_version": "1.0.0",
                "camera_settings": {
                    "resolution": "1920x1080",
                    "flash": "auto"
                },
                "location_accuracy": ${Random.nextFloat() * 10 + 3},
                "battery_level": ${Random.nextInt(20, 100)}
            }
        """.trimIndent()
    }

    // Notification Test Data
    fun createTestNotification(
        id: Long = Random.nextLong(1, 10000),
        userId: Int = Random.nextInt(1, 100),
        title: String = "Test Notification",
        message: String = "This is a test notification message for driver duties.",
        type: String = "duty_reminder",
        priority: String = "normal",
        isRead: Boolean = Random.nextBoolean(),
        createdAt: Long = System.currentTimeMillis() - Random.nextLong(0, 86400000) // Within last 24 hours
    ) = Notification(
        id = id,
        userId = userId,
        title = title,
        message = message,
        type = type,
        priority = priority,
        isRead = isRead,
        createdAt = createdAt,
        readAt = if (isRead) createdAt + Random.nextLong(1000, 3600000) else null,
        data = """{"duty_id": ${Random.nextInt(1, 1000)}, "action": "start_duty"}"""
    )

    // Command Test Data
    fun createTestCommand(
        id: Long = Random.nextLong(1, 10000),
        type: String = "SYNC_PHOTOS",
        userId: Int = Random.nextInt(1, 100),
        status: String = "pending",
        createdAt: Long = System.currentTimeMillis() - Random.nextLong(0, 3600000),
        scheduledFor: Long = System.currentTimeMillis() + Random.nextLong(0, 3600000),
        maxRetries: Int = 3,
        currentRetries: Int = 0
    ) = Command(
        id = id,
        type = type,
        userId = userId,
        status = status,
        createdAt = createdAt,
        scheduledFor = scheduledFor,
        executedAt = null,
        completedAt = null,
        maxRetries = maxRetries,
        currentRetries = currentRetries,
        data = """{"photos": [${Random.nextInt(1, 10)}], "priority": "high"}""",
        result = null,
        error = null
    )

    // Auth Models Test Data
    fun createTestSendOtpRequest(
        phoneNumber: String = "+919876543210"
    ) = SendOtpRequest(phoneNumber = phoneNumber)

    fun createTestSendOtpResponse(
        success: Boolean = true,
        message: String = "OTP sent successfully"
    ) = SendOtpResponse(success = success, message = message)

    fun createTestVerifyOtpRequest(
        phoneNumber: String = "+919876543210",
        otpCode: String = "123456",
        deviceId: String = "test_device_${Random.nextInt(1000, 9999)}"
    ) = VerifyOtpRequest(
        phoneNumber = phoneNumber,
        otpCode = otpCode,
        deviceId = deviceId
    )

    fun createTestVerifyOtpResponse(
        success: Boolean = true,
        message: String = "Login successful",
        accessToken: String? = "test_access_token_${UUID.randomUUID()}",
        refreshToken: String? = "test_refresh_token_${UUID.randomUUID()}",
        tokenExpiresIn: Long? = 3600,
        user: User? = createTestUser()
    ) = VerifyOtpResponse(
        success = success,
        message = message,
        accessToken = accessToken,
        refreshToken = refreshToken,
        tokenExpiresIn = tokenExpiresIn,
        user = user
    )

    fun createTestRefreshTokenResponse(
        success: Boolean = true,
        message: String = "Token refreshed successfully",
        accessToken: String? = "new_access_token_${UUID.randomUUID()}",
        tokenExpiresIn: Long? = 3600
    ) = RefreshTokenResponse(
        success = success,
        message = message,
        accessToken = accessToken,
        tokenExpiresIn = tokenExpiresIn
    )

    // Helper functions for creating lists
    fun createTestDutyList(count: Int = 5): List<Duty> {
        return (1..count).map { createTestDuty(id = it) }
    }

    fun createTestLocationPointList(dutyId: Int, count: Int = 10): List<LocationPoint> {
        return (1..count).map { 
            createTestLocationPoint(
                id = it.toLong(), 
                dutyId = dutyId,
                timestamp = System.currentTimeMillis() - (count - it) * 60000 // 1 minute intervals
            ) 
        }
    }

    fun createTestPhotoList(dutyId: Int, count: Int = 3): List<Photo> {
        val photoTypes = listOf("duty_start", "duty_end", "profile", "vehicle", "license")
        return (1..count).map { 
            createTestPhoto(
                id = it.toLong(),
                dutyId = dutyId,
                photoType = photoTypes[it % photoTypes.size]
            )
        }
    }

    fun createTestNotificationList(userId: Int, count: Int = 5): List<Notification> {
        return (1..count).map { 
            createTestNotification(
                id = it.toLong(),
                userId = userId,
                createdAt = System.currentTimeMillis() - it * 3600000 // 1 hour intervals
            )
        }
    }

    // Test configuration objects
    fun createTestLocationTrackingConfig() = LocationTrackingConfig(
        intervalMillis = 30000L,
        fastestIntervalMillis = 15000L,
        smallestDisplacementMeters = 10f,
        maxWaitTimeMillis = 60000L,
        accuracyThresholdMeters = 50f,
        batteryOptimizationEnabled = true
    )

    // Error scenarios for testing
    fun createNetworkErrorResponse(
        errorCode: Int = 500,
        errorMessage: String = "Internal Server Error"
    ) = mapOf(
        "error" to true,
        "code" to errorCode,
        "message" to errorMessage,
        "timestamp" to System.currentTimeMillis()
    )

    fun createAuthenticationError() = Exception("Authentication failed: Invalid token")
    fun createNetworkError() = Exception("Network error: Unable to connect to server")
    fun createDatabaseError() = Exception("Database error: Unable to perform operation")
}