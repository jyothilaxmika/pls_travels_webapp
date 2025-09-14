package com.plstravels.driver.testutils

import com.google.common.truth.Truth.assertThat
import com.plstravels.driver.data.models.*
import org.hamcrest.Description
import org.hamcrest.Matcher
import org.hamcrest.TypeSafeMatcher

/**
 * Custom matchers and assertions for testing domain objects
 * Provides fluent assertions for complex object validation
 */

// Custom Truth assertions for domain objects
fun assertThatDuty(actual: Duty) = DutySubject.assertThat(actual)
fun assertThatUser(actual: User) = UserSubject.assertThat(actual)
fun assertThatLocationPoint(actual: LocationPoint) = LocationPointSubject.assertThat(actual)
fun assertThatPhoto(actual: Photo) = PhotoSubject.assertThat(actual)

// Truth Subject for Duty
class DutySubject private constructor(
    private val actual: Duty
) {
    companion object {
        fun assertThat(actual: Duty) = DutySubject(actual)
    }

    fun hasId(expected: Int) = apply {
        assertThat(actual.id).isEqualTo(expected)
    }

    fun hasUserId(expected: Int) = apply {
        assertThat(actual.userId).isEqualTo(expected)
    }

    fun hasStatus(expected: String) = apply {
        assertThat(actual.status).isEqualTo(expected)
    }

    fun isActive() = apply {
        assertThat(actual.status).isEqualTo("active")
    }

    fun isCompleted() = apply {
        assertThat(actual.status).isEqualTo("completed")
        assertThat(actual.endTime).isNotNull()
    }

    fun hasValidLocationData() = apply {
        assertThat(actual.startLatitude).isNotNull()
        assertThat(actual.startLongitude).isNotNull()
        assertThat(actual.startLatitude).isInRange(-90.0, 90.0)
        assertThat(actual.startLongitude).isInRange(-180.0, 180.0)
    }

    fun hasPositiveDistance() = apply {
        assertThat(actual.totalDistance).isAtLeast(0.0)
    }
}

// Truth Subject for User
class UserSubject private constructor(
    private val actual: User
) {
    companion object {
        fun assertThat(actual: User) = UserSubject(actual)
    }

    fun hasId(expected: Int) = apply {
        assertThat(actual.id).isEqualTo(expected)
    }

    fun hasUsername(expected: String) = apply {
        assertThat(actual.username).isEqualTo(expected)
    }

    fun hasRole(expected: String) = apply {
        assertThat(actual.role).isEqualTo(expected)
    }

    fun isActive() = apply {
        assertThat(actual.isActive).isTrue()
    }

    fun hasValidPhoneNumber() = apply {
        assertThat(actual.phoneNumber).startsWith("+91")
        assertThat(actual.phoneNumber).hasLength(13) // +91 + 10 digits
    }
}

// Truth Subject for LocationPoint
class LocationPointSubject private constructor(
    private val actual: LocationPoint
) {
    companion object {
        fun assertThat(actual: LocationPoint) = LocationPointSubject(actual)
    }

    fun hasValidCoordinates() = apply {
        assertThat(actual.latitude).isInRange(-90.0, 90.0)
        assertThat(actual.longitude).isInRange(-180.0, 180.0)
    }

    fun hasAccuracyBetween(min: Float, max: Float) = apply {
        assertThat(actual.accuracy).isInRange(min, max)
    }

    fun hasPositiveSpeed() = apply {
        assertThat(actual.speed).isAtLeast(0f)
    }

    fun isSynced() = apply {
        assertThat(actual.isSynced).isTrue()
    }

    fun isNotSynced() = apply {
        assertThat(actual.isSynced).isFalse()
    }
}

// Truth Subject for Photo
class PhotoSubject private constructor(
    private val actual: Photo
) {
    companion object {
        fun assertThat(actual: Photo) = PhotoSubject(actual)
    }

    fun hasType(expected: String) = apply {
        assertThat(actual.photoType).isEqualTo(expected)
    }

    fun hasValidFileSize() = apply {
        assertThat(actual.fileSize).isAtLeast(1024L) // At least 1KB
        assertThat(actual.fileSize).isAtMost(10485760L) // Max 10MB
    }

    fun hasJpegMimeType() = apply {
        assertThat(actual.mimeType).isEqualTo("image/jpeg")
    }

    fun isSynced() = apply {
        assertThat(actual.isSynced).isTrue()
        assertThat(actual.uploadedAt).isNotNull()
    }

    fun isNotSynced() = apply {
        assertThat(actual.isSynced).isFalse()
        assertThat(actual.uploadedAt).isNull()
    }

    fun hasLocation() = apply {
        assertThat(actual.latitude).isNotNull()
        assertThat(actual.longitude).isNotNull()
    }
}

// Hamcrest matchers for advanced matching
class DutyMatcher {
    companion object {
        fun hasValidTimeRange(): Matcher<Duty> = object : TypeSafeMatcher<Duty>() {
            override fun describeTo(description: Description) {
                description.appendText("has valid time range (startTime <= endTime)")
            }

            override fun matchesSafely(duty: Duty): Boolean {
                return duty.endTime?.let { endTime ->
                    duty.startTime <= endTime
                } ?: true // If endTime is null, it's still valid (ongoing duty)
            }
        }

        fun isWithinDateRange(startDate: Long, endDate: Long): Matcher<Duty> = object : TypeSafeMatcher<Duty>() {
            override fun describeTo(description: Description) {
                description.appendText("is within date range $startDate - $endDate")
            }

            override fun matchesSafely(duty: Duty): Boolean {
                return duty.startTime >= startDate && duty.startTime <= endDate
            }
        }
    }
}

class LocationPointMatcher {
    companion object {
        fun isNearLocation(targetLat: Double, targetLng: Double, radiusMeters: Double): Matcher<LocationPoint> = 
            object : TypeSafeMatcher<LocationPoint>() {
                override fun describeTo(description: Description) {
                    description.appendText("is near location ($targetLat, $targetLng) within $radiusMeters meters")
                }

                override fun matchesSafely(location: LocationPoint): Boolean {
                    val distance = calculateDistance(
                        location.latitude, location.longitude,
                        targetLat, targetLng
                    )
                    return distance <= radiusMeters
                }
            }

        private fun calculateDistance(lat1: Double, lng1: Double, lat2: Double, lng2: Double): Double {
            // Simplified distance calculation for testing
            val latDiff = Math.toRadians(lat2 - lat1)
            val lngDiff = Math.toRadians(lng2 - lng1)
            val a = Math.sin(latDiff / 2) * Math.sin(latDiff / 2) +
                    Math.cos(Math.toRadians(lat1)) * Math.cos(Math.toRadians(lat2)) *
                    Math.sin(lngDiff / 2) * Math.sin(lngDiff / 2)
            val c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
            return 6371000 * c // Earth radius in meters
        }
    }
}

// Extension functions for common assertions
fun <T> List<T>.shouldHaveSize(expectedSize: Int) = apply {
    assertThat(this).hasSize(expectedSize)
}

fun <T> List<T>.shouldNotBeEmpty() = apply {
    assertThat(this).isNotEmpty()
}

fun <T> List<T>.shouldContain(element: T) = apply {
    assertThat(this).contains(element)
}

// Result assertions
fun <T> Result<T>.shouldBeSuccess() = apply {
    assertThat(this.isSuccess).isTrue()
}

fun <T> Result<T>.shouldBeFailure() = apply {
    assertThat(this.isFailure).isTrue()
}

fun <T> Result<T>.shouldHaveValue(expected: T) = apply {
    shouldBeSuccess()
    assertThat(this.getOrNull()).isEqualTo(expected)
}

fun <T> Result<T>.shouldHaveError(expectedMessage: String) = apply {
    shouldBeFailure()
    assertThat(this.exceptionOrNull()?.message).contains(expectedMessage)
}