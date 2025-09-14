package com.plstravels.driver.testutils

import com.plstravels.driver.data.local.PLSDatabase
import com.plstravels.driver.testutils.mocks.MockProviders
import com.plstravels.driver.testutils.rules.DatabaseRule
import kotlinx.coroutines.ExperimentalCoroutinesApi
import org.junit.Rule

/**
 * Base class for repository tests providing database and common mocks
 * Extends BaseUnitTest with database-specific setup
 */
@ExperimentalCoroutinesApi
abstract class BaseRepositoryTest : BaseUnitTest() {

    @get:Rule
    val databaseRule = DatabaseRule()

    protected val database: PLSDatabase
        get() = databaseRule.database

    // Common mocks available to all repository tests
    protected val mockApiService = MockProviders.createMockApiService()
    protected val mockTokenManager = MockProviders.createMockTokenManager()
    protected val mockConnectivityRepository = MockProviders.createMockConnectivityRepository()

    override fun setUp() {
        super.setUp()
        // Additional repository-specific setup can be added here
    }
}