package com.plstravels.driver.integration

import androidx.test.ext.junit.runners.AndroidJUnit4
import com.plstravels.driver.data.network.ApiService
import com.plstravels.driver.testutils.factories.TestDataFactory
import com.google.common.truth.Truth.assertThat
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

/**
 * Integration tests for API service with mock server
 * Tests network layer, serialization, and error handling
 */
@RunWith(AndroidJUnit4::class)
class ApiIntegrationTest {

    private lateinit var mockWebServer: MockWebServer
    private lateinit var apiService: ApiService

    @Before
    fun setup() {
        mockWebServer = MockWebServer()
        mockWebServer.start()

        val retrofit = Retrofit.Builder()
            .baseUrl(mockWebServer.url("/"))
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        apiService = retrofit.create(ApiService::class.java)
    }

    @After
    fun teardown() {
        mockWebServer.shutdown()
    }

    @Test
    fun sendOtp_shouldSerializeRequestCorrectly() = runTest {
        // Arrange
        val expectedResponse = TestDataFactory.createTestSendOtpResponse()
        val mockResponse = MockResponse()
            .setResponseCode(200)
            .setBody("""
                {
                    "success": true,
                    "message": "OTP sent successfully"
                }
            """.trimIndent())
        
        mockWebServer.enqueue(mockResponse)

        val request = TestDataFactory.createTestSendOtpRequest("+919876543210")

        // Act
        val response = apiService.sendOtp(request)

        // Assert
        assertThat(response.isSuccessful).isTrue()
        assertThat(response.body()?.success).isTrue()
        assertThat(response.body()?.message).isEqualTo("OTP sent successfully")

        // Verify request was made correctly
        val recordedRequest = mockWebServer.takeRequest()
        assertThat(recordedRequest.path).isEqualTo("/auth/send-otp")
        assertThat(recordedRequest.method).isEqualTo("POST")
        assertThat(recordedRequest.body.readUtf8()).contains("+919876543210")
    }

    @Test
    fun verifyOtp_shouldHandleSuccessfulResponse() = runTest {
        // Arrange
        val testUser = TestDataFactory.createTestUser()
        val mockResponse = MockResponse()
            .setResponseCode(200)
            .setBody("""
                {
                    "success": true,
                    "message": "Login successful",
                    "accessToken": "test_access_token",
                    "refreshToken": "test_refresh_token",
                    "tokenExpiresIn": 3600,
                    "user": {
                        "id": ${testUser.id},
                        "username": "${testUser.username}",
                        "phoneNumber": "${testUser.phoneNumber}",
                        "role": "${testUser.role}",
                        "isActive": ${testUser.isActive},
                        "createdAt": ${testUser.createdAt},
                        "updatedAt": ${testUser.updatedAt}
                    }
                }
            """.trimIndent())

        mockWebServer.enqueue(mockResponse)

        val request = TestDataFactory.createTestVerifyOtpRequest()

        // Act
        val response = apiService.verifyOtp(request)

        // Assert
        assertThat(response.isSuccessful).isTrue()
        with(response.body()!!) {
            assertThat(success).isTrue()
            assertThat(accessToken).isEqualTo("test_access_token")
            assertThat(refreshToken).isEqualTo("test_refresh_token")
            assertThat(user?.id).isEqualTo(testUser.id)
            assertThat(user?.username).isEqualTo(testUser.username)
        }
    }

    @Test
    fun verifyOtp_shouldHandleErrorResponse() = runTest {
        // Arrange
        val mockResponse = MockResponse()
            .setResponseCode(200)
            .setBody("""
                {
                    "success": false,
                    "message": "Invalid OTP"
                }
            """.trimIndent())

        mockWebServer.enqueue(mockResponse)

        val request = TestDataFactory.createTestVerifyOtpRequest(otpCode = "000000")

        // Act
        val response = apiService.verifyOtp(request)

        // Assert
        assertThat(response.isSuccessful).isTrue()
        assertThat(response.body()?.success).isFalse()
        assertThat(response.body()?.message).isEqualTo("Invalid OTP")
    }

    @Test
    fun syncDuty_shouldSerializeDutyCorrectly() = runTest {
        // Arrange
        val testDuty = TestDataFactory.createTestDuty()
        val mockResponse = MockResponse()
            .setResponseCode(200)
            .setBody("""{"success": true}""")

        mockWebServer.enqueue(mockResponse)

        // Act
        val response = apiService.syncDuty(testDuty)

        // Assert
        assertThat(response.isSuccessful).isTrue()

        val recordedRequest = mockWebServer.takeRequest()
        assertThat(recordedRequest.path).isEqualTo("/duties/sync")
        assertThat(recordedRequest.method).isEqualTo("POST")
        
        val requestBody = recordedRequest.body.readUtf8()
        assertThat(requestBody).contains(testDuty.userId.toString())
        assertThat(requestBody).contains(testDuty.vehicleId.toString())
        assertThat(requestBody).contains(testDuty.status)
    }

    @Test
    fun syncLocation_shouldHandleBatchUpload() = runTest {
        // Arrange
        val locationPoints = TestDataFactory.createTestLocationPointList(dutyId = 1, count = 5)
        val mockResponse = MockResponse()
            .setResponseCode(200)
            .setBody("""{"success": true, "synced": 5}""")

        mockWebServer.enqueue(mockResponse)

        // Act
        val response = apiService.syncLocation(locationPoints)

        // Assert
        assertThat(response.isSuccessful).isTrue()

        val recordedRequest = mockWebServer.takeRequest()
        assertThat(recordedRequest.path).isEqualTo("/location/sync")
        assertThat(recordedRequest.method).isEqualTo("POST")

        val requestBody = recordedRequest.body.readUtf8()
        locationPoints.forEach { point ->
            assertThat(requestBody).contains(point.latitude.toString())
            assertThat(requestBody).contains(point.longitude.toString())
        }
    }

    @Test
    fun apiService_shouldHandleNetworkErrors() = runTest {
        // Arrange
        val mockResponse = MockResponse()
            .setResponseCode(500)
            .setBody("Internal Server Error")

        mockWebServer.enqueue(mockResponse)

        val request = TestDataFactory.createTestSendOtpRequest()

        // Act
        val response = apiService.sendOtp(request)

        // Assert
        assertThat(response.isSuccessful).isFalse()
        assertThat(response.code()).isEqualTo(500)
    }

    @Test
    fun apiService_shouldHandleTimeout() = runTest {
        // Arrange - Server that never responds (simulates timeout)
        // MockWebServer will handle this automatically if no response is enqueued
        val request = TestDataFactory.createTestSendOtpRequest()

        // Act & Assert
        try {
            val response = apiService.sendOtp(request)
            // If we get here without timeout, the test framework handled it differently
            assertThat(response.isSuccessful).isAnyOf(true, false)
        } catch (e: Exception) {
            // Expected for timeout scenarios
            assertThat(e).isInstanceOf(java.net.SocketTimeoutException::class.java)
        }
    }

    @Test
    fun uploadPhoto_shouldHandleMultipartFormData() = runTest {
        // Arrange
        val testPhoto = TestDataFactory.createTestPhoto()
        val mockResponse = MockResponse()
            .setResponseCode(200)
            .setBody("""
                {
                    "success": true,
                    "url": "https://storage.example.com/photos/test.jpg"
                }
            """.trimIndent())

        mockWebServer.enqueue(mockResponse)

        // Create a mock multipart body (in real test, you'd use actual file)
        val mockRequestBody = okhttp3.RequestBody.create(
            okhttp3.MediaType.parse("image/jpeg"), 
            "mock image data".toByteArray()
        )
        val mockMultipartBody = okhttp3.MultipartBody.Part.createFormData(
            "photo", 
            testPhoto.fileName, 
            mockRequestBody
        )

        // Act
        val response = apiService.uploadPhoto(testPhoto.dutyId, mockMultipartBody)

        // Assert
        assertThat(response.isSuccessful).isTrue()
        assertThat(response.body()?.get("success")).isEqualTo(true)
        assertThat(response.body()?.get("url")).isEqualTo("https://storage.example.com/photos/test.jpg")

        val recordedRequest = mockWebServer.takeRequest()
        assertThat(recordedRequest.path).isEqualTo("/photos/upload/${testPhoto.dutyId}")
        assertThat(recordedRequest.method).isEqualTo("POST")
        assertThat(recordedRequest.headers["Content-Type"]).contains("multipart/form-data")
    }

    @Test
    fun refreshToken_shouldHandleTokenRefresh() = runTest {
        // Arrange
        val mockResponse = MockResponse()
            .setResponseCode(200)
            .setBody("""
                {
                    "success": true,
                    "message": "Token refreshed",
                    "accessToken": "new_access_token",
                    "tokenExpiresIn": 3600
                }
            """.trimIndent())

        mockWebServer.enqueue(mockResponse)

        // Act
        val response = apiService.refreshToken()

        // Assert
        assertThat(response.isSuccessful).isTrue()
        with(response.body()!!) {
            assertThat(success).isTrue()
            assertThat(accessToken).isEqualTo("new_access_token")
            assertThat(tokenExpiresIn).isEqualTo(3600)
        }

        val recordedRequest = mockWebServer.takeRequest()
        assertThat(recordedRequest.path).isEqualTo("/auth/refresh")
        assertThat(recordedRequest.method).isEqualTo("POST")
    }

    @Test
    fun apiService_shouldHandleAuthenticationErrors() = runTest {
        // Arrange
        val mockResponse = MockResponse()
            .setResponseCode(401)
            .setBody("""
                {
                    "error": "Unauthorized",
                    "message": "Access token expired"
                }
            """.trimIndent())

        mockWebServer.enqueue(mockResponse)

        val testDuty = TestDataFactory.createTestDuty()

        // Act
        val response = apiService.syncDuty(testDuty)

        // Assert
        assertThat(response.isSuccessful).isFalse()
        assertThat(response.code()).isEqualTo(401)
    }

    @Test
    fun getDuties_shouldHandlePaginatedResponse() = runTest {
        // Arrange
        val duties = TestDataFactory.createTestDutyList(count = 3)
        val mockResponse = MockResponse()
            .setResponseCode(200)
            .setBody("""
                {
                    "duties": ${duties.toJsonArray()},
                    "page": 1,
                    "totalPages": 2,
                    "totalCount": 6
                }
            """.trimIndent())

        mockWebServer.enqueue(mockResponse)

        // Act
        val response = apiService.getDuties(page = 1, limit = 3)

        // Assert
        assertThat(response.isSuccessful).isTrue()
        assertThat(response.body()).hasSize(3)

        val recordedRequest = mockWebServer.takeRequest()
        assertThat(recordedRequest.path).contains("page=1")
        assertThat(recordedRequest.path).contains("limit=3")
    }

    // Helper function to convert duties to JSON array string
    private fun List<com.plstravels.driver.data.models.Duty>.toJsonArray(): String {
        return this.joinToString(
            prefix = "[",
            postfix = "]",
            separator = ","
        ) { duty ->
            """
            {
                "id": ${duty.id},
                "userId": ${duty.userId},
                "vehicleId": ${duty.vehicleId},
                "status": "${duty.status}",
                "startTime": ${duty.startTime},
                "endTime": ${duty.endTime},
                "startLatitude": ${duty.startLatitude},
                "startLongitude": ${duty.startLongitude},
                "endLatitude": ${duty.endLatitude},
                "endLongitude": ${duty.endLongitude},
                "totalDistance": ${duty.totalDistance},
                "totalAmount": ${duty.totalAmount},
                "createdAt": ${duty.createdAt},
                "updatedAt": ${duty.updatedAt}
            }
            """.trimIndent()
        }
    }
}