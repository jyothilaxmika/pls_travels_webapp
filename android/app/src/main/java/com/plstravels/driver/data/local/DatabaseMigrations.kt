package com.plstravels.driver.data.local

import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

/**
 * Database migrations for Room database
 */
object DatabaseMigrations {
    
    /**
     * Migration from version 4 to 5
     * Adds QueuedCommand table for offline command queue functionality
     */
    val MIGRATION_4_5 = object : Migration(4, 5) {
        override fun migrate(database: SupportSQLiteDatabase) {
            // Create command_queue table
            database.execSQL("""
                CREATE TABLE IF NOT EXISTS `command_queue` (
                    `id` TEXT NOT NULL,
                    `type` TEXT NOT NULL,
                    `payload` TEXT NOT NULL,
                    `timestamp` INTEGER NOT NULL,
                    `retryCount` INTEGER NOT NULL DEFAULT 0,
                    `maxRetries` INTEGER NOT NULL DEFAULT 3,
                    `isExecuting` INTEGER NOT NULL DEFAULT 0,
                    `lastError` TEXT,
                    `idempotencyKey` TEXT,
                    `tempEntityId` TEXT,
                    `serverEntityId` TEXT,
                    `isReconciled` INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(`id`)
                )
            """.trimIndent())
            
            // Create index for better query performance
            database.execSQL("""
                CREATE INDEX IF NOT EXISTS `index_command_queue_type_timestamp` 
                ON `command_queue` (`type`, `timestamp`)
            """.trimIndent())
            
            database.execSQL("""
                CREATE INDEX IF NOT EXISTS `index_command_queue_isExecuting` 
                ON `command_queue` (`isExecuting`)
            """.trimIndent())
            
            database.execSQL("""
                CREATE INDEX IF NOT EXISTS `index_command_queue_idempotencyKey` 
                ON `command_queue` (`idempotencyKey`)
            """.trimIndent())
        }
    }
    
    /**
     * Get all migrations
     */
    fun getAllMigrations(): Array<Migration> {
        return arrayOf(MIGRATION_4_5)
    }
}