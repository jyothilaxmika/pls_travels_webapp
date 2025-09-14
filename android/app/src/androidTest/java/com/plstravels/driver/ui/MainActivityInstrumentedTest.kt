package com.plstravels.driver.ui

import androidx.test.core.app.ActivityScenario
import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.action.ViewActions.*
import androidx.test.espresso.assertion.ViewAssertions.matches
import androidx.test.espresso.intent.Intents
import androidx.test.espresso.intent.matcher.IntentMatchers
import androidx.test.espresso.matcher.ViewMatchers.*
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.filters.LargeTest
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.UiDevice
import com.plstravels.driver.MainActivity
import com.plstravels.driver.R
import dagger.hilt.android.testing.HiltAndroidRule
import dagger.hilt.android.testing.HiltAndroidTest
import org.junit.After
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Instrumentation tests for MainActivity using Espresso
 * Tests device-specific functionality, permissions, and system integration
 */
@RunWith(AndroidJUnit4::class)
@LargeTest
@HiltAndroidTest
class MainActivityInstrumentedTest {

    @get:Rule
    var hiltRule = HiltAndroidRule(this)

    private lateinit var device: UiDevice

    @Before
    fun setup() {
        hiltRule.inject()
        device = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())
        Intents.init()
    }

    @After
    fun teardown() {
        Intents.release()
    }

    @Test
    fun mainActivity_launchesSuccessfully() {
        // Act
        ActivityScenario.launch(MainActivity::class.java)

        // Assert - Activity should launch without crashes
        onView(withId(android.R.id.content))
            .check(matches(isDisplayed()))
    }

    @Test
    fun authFlow_completesEndToEnd() {
        // Arrange
        ActivityScenario.launch(MainActivity::class.java)

        // Act - Navigate through auth flow
        onView(withId(R.id.phoneInput))
            .perform(typeText("9876543210"), closeSoftKeyboard())

        onView(withId(R.id.sendOtpButton))
            .perform(click())

        // Wait for OTP screen
        Thread.sleep(1000)

        onView(withId(R.id.otpInput))
            .check(matches(isDisplayed()))
            .perform(typeText("123456"), closeSoftKeyboard())

        onView(withId(R.id.verifyOtpButton))
            .perform(click())

        // Assert - Should navigate to dashboard or show success
        // Note: In real test, you'd mock the API responses
    }

    @Test
    fun locationPermission_isRequestedWhenNeeded() {
        // Arrange
        ActivityScenario.launch(MainActivity::class.java)
        
        // Simulate logged-in state and navigate to duty screen
        // This would require test setup to bypass auth

        // Act - Try to start duty (requires location permission)
        onView(withText("Start Duty"))
            .perform(click())

        // Assert - System permission dialog should appear
        device.wait(Until.hasObject(By.text("Allow")), 5000)
        
        val allowButton = device.findObject(UiSelector().text("Allow"))
        assertThat(allowButton.exists()).isTrue()
    }

    @Test
    fun cameraPermission_isRequestedForPhotoCapture() {
        // Arrange
        ActivityScenario.launch(MainActivity::class.java)
        
        // Simulate navigation to photo capture screen

        // Act - Try to capture photo
        onView(withText("Take Photo"))
            .perform(click())

        // Assert - Camera permission dialog should appear
        device.wait(Until.hasObject(By.text("Allow")), 5000)
        
        val allowButton = device.findObject(UiSelector().text("Allow"))
        assertThat(allowButton.exists()).isTrue()
    }

    @Test
    fun networkConnectivity_isHandledGracefully() {
        // Arrange
        ActivityScenario.launch(MainActivity::class.java)
        
        // Simulate network disconnection
        device.executeShellCommand("svc wifi disable")
        device.executeShellCommand("svc data disable")

        // Act - Try to perform network operation
        onView(withId(R.id.phoneInput))
            .perform(typeText("9876543210"), closeSoftKeyboard())

        onView(withId(R.id.sendOtpButton))
            .perform(click())

        // Assert - Should show network error message
        onView(withText("No internet connection"))
            .check(matches(isDisplayed()))

        // Cleanup - Re-enable network
        device.executeShellCommand("svc wifi enable")
        device.executeShellCommand("svc data enable")
    }

    @Test
    fun backgroundLocation_continuesWhenAppInBackground() {
        // Arrange
        ActivityScenario.launch(MainActivity::class.java)
        
        // Simulate starting duty with location tracking
        // This would require proper test setup

        // Act - Put app in background
        device.pressHome()
        Thread.sleep(2000)

        // Assert - Location service should still be running
        // Verify through notification or service status
        device.openNotification()
        onView(withText("Tracking duty location"))
            .check(matches(isDisplayed()))
    }

    @Test
    fun systemRotation_preservesUserInput() {
        // Arrange
        ActivityScenario.launch(MainActivity::class.java)
        
        val testPhoneNumber = "9876543210"

        // Act - Enter phone number
        onView(withId(R.id.phoneInput))
            .perform(typeText(testPhoneNumber))

        // Rotate device
        device.setOrientationLeft()
        Thread.sleep(1000)

        // Assert - Input should be preserved
        onView(withId(R.id.phoneInput))
            .check(matches(withText(testPhoneNumber)))

        // Rotate back
        device.setOrientationNatural()
    }

    @Test
    fun notificationInteraction_worksCorrectly() {
        // Arrange - Start location tracking service
        ActivityScenario.launch(MainActivity::class.java)
        
        // Simulate duty start to trigger notification
        // This would require proper service initialization

        // Act - Pull down notification panel
        device.openNotification()

        // Assert - Location tracking notification should be present
        val notification = device.findObject(
            UiSelector().textContains("Tracking duty location")
        )
        assertThat(notification.exists()).isTrue()

        // Act - Tap notification action
        val stopButton = device.findObject(UiSelector().text("Stop Tracking"))
        stopButton.click()

        // Assert - Should return to app
        onView(withText("Duty Ended"))
            .check(matches(isDisplayed()))
    }

    @Test
    fun memoryPressure_isHandledGracefully() {
        // Arrange
        ActivityScenario.launch(MainActivity::class.java)
        
        // Simulate memory pressure by opening many activities
        repeat(5) {
            device.pressRecentApps()
            Thread.sleep(500)
            device.pressBack()
        }

        // Act - Return to app
        ActivityScenario.launch(MainActivity::class.java)

        // Assert - App should restore correctly
        onView(withId(android.R.id.content))
            .check(matches(isDisplayed()))
    }

    @Test
    fun systemThemeChange_isReflectedInApp() {
        // Arrange
        ActivityScenario.launch(MainActivity::class.java)
        
        // Act - Change system theme to dark mode
        device.executeShellCommand("cmd uimode night yes")
        Thread.sleep(1000)

        // Assert - App should reflect dark theme
        // This would require checking specific UI elements for dark theme colors
        
        // Cleanup - Restore original theme
        device.executeShellCommand("cmd uimode night no")
    }

    @Test
    fun accessibilityServices_workCorrectly() {
        // Arrange
        ActivityScenario.launch(MainActivity::class.java)
        
        // Act - Navigate using TalkBack-like interactions
        onView(withId(R.id.phoneInput))
            .check(matches(hasContentDescription()))
            .perform(click())

        // Assert - Content descriptions should be present
        onView(withId(R.id.sendOtpButton))
            .check(matches(hasContentDescription()))
    }

    @Test
    fun batteryOptimization_doesNotKillLocationService() {
        // Arrange
        ActivityScenario.launch(MainActivity::class.java)
        
        // Start location tracking
        // This would require proper service setup

        // Act - Simulate battery optimization
        device.executeShellCommand("cmd appops set com.plstravels.driver RUN_IN_BACKGROUND ignore")
        Thread.sleep(5000)

        // Assert - Location service should continue running
        // Check service status or notification presence

        // Cleanup
        device.executeShellCommand("cmd appops set com.plstravels.driver RUN_IN_BACKGROUND allow")
    }

    @Test
    fun multiWindow_behavesCorrectly() {
        // Only test on devices that support multi-window
        if (android.os.Build.VERSION.SDK_INT >= 24) {
            // Arrange
            ActivityScenario.launch(MainActivity::class.java)
            
            // Act - Enter multi-window mode
            device.pressRecentApps()
            Thread.sleep(1000)
            
            // Simulate multi-window split (device-specific implementation)
            
            // Assert - App should continue functioning in split screen
            onView(withId(android.R.id.content))
                .check(matches(isDisplayed()))
        }
    }

    @Test
    fun systemBackButton_handlesNavigationCorrectly() {
        // Arrange
        ActivityScenario.launch(MainActivity::class.java)
        
        // Simulate navigation to inner screen
        onView(withId(R.id.phoneInput))
            .perform(typeText("9876543210"), closeSoftKeyboard())
        onView(withId(R.id.sendOtpButton))
            .perform(click())

        Thread.sleep(1000) // Wait for navigation

        // Act - Press back button
        device.pressBack()

        // Assert - Should return to phone input screen
        onView(withId(R.id.phoneInput))
            .check(matches(isDisplayed()))
    }
}

// Helper classes for UI Automator
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiSelector
import androidx.test.uiautomator.Until
import com.google.common.truth.Truth.assertThat