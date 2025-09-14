package com.plstravels.driver.testutils.rules

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.*
import org.junit.rules.TestWatcher
import org.junit.runner.Description

/**
 * JUnit rule to set up and tear down coroutine test environment
 * Provides TestCoroutineScheduler for controlling coroutine execution in tests
 */
@ExperimentalCoroutinesApi
class TestCoroutineRule(
    val testDispatcher: TestDispatcher = UnconfinedTestDispatcher()
) : TestWatcher() {

    override fun starting(description: Description) {
        super.starting(description)
        Dispatchers.setMain(testDispatcher)
    }

    override fun finished(description: Description) {
        super.finished(description)
        Dispatchers.resetMain()
    }

    /**
     * Run test block with the test dispatcher
     */
    fun runTest(block: suspend TestScope.() -> Unit) = kotlinx.coroutines.test.runTest(testDispatcher) {
        block()
    }
}