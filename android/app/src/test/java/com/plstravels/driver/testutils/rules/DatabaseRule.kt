package com.plstravels.driver.testutils.rules

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import com.plstravels.driver.data.local.PLSDatabase
import org.junit.rules.TestWatcher
import org.junit.runner.Description
import java.io.IOException

/**
 * JUnit rule to set up and tear down in-memory database for testing
 * Provides clean database instance for each test
 */
class DatabaseRule : TestWatcher() {
    
    lateinit var database: PLSDatabase
        private set

    override fun starting(description: Description) {
        super.starting(description)
        database = Room.inMemoryDatabaseBuilder(
            ApplicationProvider.getApplicationContext(),
            PLSDatabase::class.java
        )
            .allowMainThreadQueries() // For testing only
            .build()
    }

    override fun finished(description: Description) {
        super.finished(description)
        try {
            database.close()
        } catch (e: IOException) {
            // Handle close error
        }
    }
}