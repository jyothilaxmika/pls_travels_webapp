package com.plstravels.driver.testutils

import androidx.arch.core.executor.testing.InstantTaskExecutorRule
import com.plstravels.driver.testutils.rules.TestCoroutineRule
import io.mockk.clearAllMocks
import kotlinx.coroutines.ExperimentalCoroutinesApi
import org.junit.After
import org.junit.Before
import org.junit.Rule

/**
 * Base class for unit tests providing common setup and teardown
 * Handles coroutine testing, LiveData testing, and mock cleanup
 */
@ExperimentalCoroutinesApi
abstract class BaseUnitTest {

    // Rule to handle LiveData and Architecture Components
    @get:Rule
    val instantTaskExecutorRule = InstantTaskExecutorRule()

    // Rule to handle coroutines in tests
    @get:Rule
    val testCoroutineRule = TestCoroutineRule()

    @Before
    open fun setUp() {
        // Override in subclasses for additional setup
    }

    @After
    open fun tearDown() {
        // Clear all mocks after each test
        clearAllMocks()
    }

    /**
     * Run test with coroutines
     */
    protected fun runTest(block: suspend () -> Unit) = testCoroutineRule.runTest {
        block()
    }
}