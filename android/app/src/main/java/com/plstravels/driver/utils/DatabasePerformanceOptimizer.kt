package com.plstravels.driver.utils

import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.sqlite.db.SupportSQLiteDatabase
import com.plstravels.driver.data.local.PLSDatabase
import kotlinx.coroutines.*
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Database performance optimizer for Room database
 * Handles indexing, query optimization, and batch processing
 */
@Singleton
class DatabasePerformanceOptimizer @Inject constructor(
    private val database: PLSDatabase,
    private val logger: ProdLogger
) {
    
    private val optimizationScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    
    companion object {
        private const val TAG = "DatabasePerformanceOptimizer"
        private const val BATCH_SIZE_SMALL = 50
        private const val BATCH_SIZE_MEDIUM = 100
        private const val BATCH_SIZE_LARGE = 500
        private const val VACUUM_INTERVAL_MS = 24 * 60 * 60 * 1000L // 24 hours
    }
    
    data class OptimizationMetrics(
        val totalQueries: Long = 0,
        val slowQueries: Long = 0,
        val averageQueryTime: Double = 0.0,
        val cacheHitRate: Double = 0.0,
        val databaseSize: Long = 0,
        val lastVacuumTime: Long = 0
    )
    
    private var metrics = OptimizationMetrics()
    private var lastVacuumTime = 0L
    
    fun initialize() {
        optimizationScope.launch {
            createOptimalIndexes()
            configureDatabase()
            scheduleMaintenanceTasks()
        }
        logger.i(TAG, "Database performance optimizer initialized")
    }
    
    /**
     * Create optimal indexes for frequently used queries
     */
    private suspend fun createOptimalIndexes() {
        withContext(Dispatchers.IO) {
            try {
                database.openHelper.writableDatabase.apply {
                    // Location points optimization
                    execSQL("CREATE INDEX IF NOT EXISTS idx_location_points_duty_timestamp ON location_points(duty_id, timestamp)")
                    execSQL("CREATE INDEX IF NOT EXISTS idx_location_points_sync_status ON location_points(is_synced, sync_retry_count)")
                    execSQL("CREATE INDEX IF NOT EXISTS idx_location_points_cleanup ON location_points(is_synced, created_at)")
                    
                    // Duties optimization
                    execSQL("CREATE INDEX IF NOT EXISTS idx_duties_status_created ON duties(status, created_at)")
                    execSQL("CREATE INDEX IF NOT EXISTS idx_duties_sync_status ON duties(sync_status)")
                    execSQL("CREATE INDEX IF NOT EXISTS idx_duties_driver_status ON duties(driver_id, status)")
                    
                    // Photos optimization
                    execSQL("CREATE INDEX IF NOT EXISTS idx_photos_duty_type ON photos(duty_id, photo_type)")
                    execSQL("CREATE INDEX IF NOT EXISTS idx_photos_sync_status ON photos(is_synced, sync_retry_count)")
                    execSQL("CREATE INDEX IF NOT EXISTS idx_photos_path ON photos(local_path)")
                    
                    // Notifications optimization
                    execSQL("CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications(user_id, is_read)")
                    execSQL("CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at)")
                    
                    // Command queue optimization
                    execSQL("CREATE INDEX IF NOT EXISTS idx_command_queue_status_priority ON queued_commands(status, priority)")
                    execSQL("CREATE INDEX IF NOT EXISTS idx_command_queue_created ON queued_commands(created_at)")
                    
                    // Location sessions optimization
                    execSQL("CREATE INDEX IF NOT EXISTS idx_location_sessions_duty_active ON location_sessions(duty_id, is_active)")
                    execSQL("CREATE INDEX IF NOT EXISTS idx_location_sessions_start_time ON location_sessions(start_time)")
                }
                
                logger.i(TAG, "Database indexes created successfully")
            } catch (e: Exception) {
                logger.e(TAG, "Error creating database indexes", throwable = e)
            }
        }
    }
    
    /**
     * Configure database for optimal performance
     */
    private suspend fun configureDatabase() {
        withContext(Dispatchers.IO) {
            try {
                database.openHelper.writableDatabase.apply {
                    // Enable WAL mode for better concurrency
                    execSQL("PRAGMA journal_mode=WAL")
                    
                    // Optimize synchronization
                    execSQL("PRAGMA synchronous=NORMAL")
                    
                    // Set cache size (negative value means KB)
                    execSQL("PRAGMA cache_size=-10240") // 10MB cache
                    
                    // Optimize temp storage
                    execSQL("PRAGMA temp_store=MEMORY")
                    
                    // Enable query planner optimization
                    execSQL("PRAGMA optimize")
                    
                    // Set busy timeout
                    execSQL("PRAGMA busy_timeout=30000") // 30 seconds
                    
                    // Foreign key constraints
                    execSQL("PRAGMA foreign_keys=ON")
                }
                
                logger.i(TAG, "Database configuration optimized")
            } catch (e: Exception) {
                logger.e(TAG, "Error configuring database", throwable = e)
            }
        }
    }
    
    /**
     * Schedule maintenance tasks like VACUUM and ANALYZE
     */
    private fun scheduleMaintenanceTasks() {
        optimizationScope.launch {
            while (isActive) {
                try {
                    delay(VACUUM_INTERVAL_MS)
                    performMaintenance()
                } catch (e: Exception) {
                    logger.e(TAG, "Error during maintenance", throwable = e)
                    delay(VACUUM_INTERVAL_MS / 2) // Retry sooner on error
                }
            }
        }
    }
    
    /**
     * Perform database maintenance
     */
    suspend fun performMaintenance() {
        withContext(Dispatchers.IO) {
            try {
                val startTime = System.currentTimeMillis()
                
                database.openHelper.writableDatabase.apply {
                    // Update query planner statistics
                    execSQL("ANALYZE")
                    
                    // Check if VACUUM is needed
                    if (shouldPerformVacuum()) {
                        logger.i(TAG, "Performing database VACUUM")
                        execSQL("VACUUM")
                        lastVacuumTime = System.currentTimeMillis()
                    }
                    
                    // Optimize query planner
                    execSQL("PRAGMA optimize")
                }
                
                val duration = System.currentTimeMillis() - startTime
                logger.i(TAG, "Database maintenance completed", mapOf(
                    "duration_ms" to duration.toString(),
                    "vacuum_performed" to (lastVacuumTime > startTime - 1000).toString()
                ))
                
            } catch (e: Exception) {
                logger.e(TAG, "Error during database maintenance", throwable = e)
            }
        }
    }
    
    private fun shouldPerformVacuum(): Boolean {
        val currentTime = System.currentTimeMillis()
        return (currentTime - lastVacuumTime) > VACUUM_INTERVAL_MS
    }
    
    /**
     * Batch process location points for better performance
     */
    suspend fun batchProcessLocationPoints(
        points: List<Any>,
        operation: suspend (List<Any>) -> Unit
    ) {
        withContext(Dispatchers.IO) {
            val batchSize = when {
                points.size < 100 -> BATCH_SIZE_SMALL
                points.size < 1000 -> BATCH_SIZE_MEDIUM
                else -> BATCH_SIZE_LARGE
            }
            
            points.chunked(batchSize).forEach { batch ->
                try {
                    database.runInTransaction {
                        runBlocking {
                            operation(batch)
                        }
                    }
                } catch (e: Exception) {
                    logger.e(TAG, "Error in batch operation", mapOf(
                        "batch_size" to batch.size.toString()
                    ), e)
                    
                    // Try individual processing as fallback
                    batch.forEach { item ->
                        try {
                            operation(listOf(item))
                        } catch (itemError: Exception) {
                            logger.e(TAG, "Error processing individual item", throwable = itemError)
                        }
                    }
                }
            }
        }
    }
    
    /**
     * Optimize query execution with monitoring
     */
    suspend fun <T> executeOptimizedQuery(
        queryName: String,
        query: suspend () -> T
    ): T {
        val startTime = System.currentTimeMillis()
        
        return try {
            val result = query()
            val duration = System.currentTimeMillis() - startTime
            
            updateMetrics(queryName, duration)
            
            if (duration > 1000) { // Log slow queries (>1 second)
                logger.w(TAG, "Slow query detected: $queryName", mapOf(
                    "duration_ms" to duration.toString()
                ))
            }
            
            result
        } catch (e: Exception) {
            val duration = System.currentTimeMillis() - startTime
            logger.e(TAG, "Query failed: $queryName", mapOf(
                "duration_ms" to duration.toString()
            ), e)
            throw e
        }
    }
    
    private fun updateMetrics(queryName: String, duration: Long) {
        metrics = metrics.copy(
            totalQueries = metrics.totalQueries + 1,
            slowQueries = metrics.slowQueries + if (duration > 1000) 1 else 0,
            averageQueryTime = (metrics.averageQueryTime * (metrics.totalQueries - 1) + duration) / metrics.totalQueries
        )
    }
    
    /**
     * Clean up old data to maintain performance
     */
    suspend fun performDataCleanup() {
        withContext(Dispatchers.IO) {
            try {
                val cutoffTime = System.currentTimeMillis() - (30 * 24 * 60 * 60 * 1000L) // 30 days
                
                database.runInTransaction {
                    // Clean up old synced location points
                    database.locationDao().deleteOldSyncedLocationPoints(cutoffTime)
                    
                    // Clean up failed sync attempts
                    database.locationDao().deleteFailedSyncLocationPoints(maxRetries = 5, cutoffTime)
                    
                    // Clean up old notifications
                    database.notificationDao().deleteOldNotifications(cutoffTime)
                    
                    // Clean up completed commands
                    database.commandQueueDao().deleteCompletedCommands(cutoffTime)
                }
                
                logger.i(TAG, "Data cleanup completed", mapOf(
                    "cutoff_days" to "30"
                ))
                
            } catch (e: Exception) {
                logger.e(TAG, "Error during data cleanup", throwable = e)
            }
        }
    }
    
    /**
     * Get performance metrics
     */
    fun getMetrics(): OptimizationMetrics {
        return metrics.copy(
            databaseSize = getDatabaseSize(),
            lastVacuumTime = lastVacuumTime
        )
    }
    
    private fun getDatabaseSize(): Long {
        return try {
            database.openHelper.readableDatabase.pageCount * database.openHelper.readableDatabase.pageSize
        } catch (e: Exception) {
            logger.e(TAG, "Error getting database size", throwable = e)
            0L
        }
    }
    
    /**
     * Analyze and report query performance
     */
    suspend fun analyzeQueryPerformance(): Map<String, Any> {
        return withContext(Dispatchers.IO) {
            try {
                val queryPlan = mutableMapOf<String, Any>()
                
                database.openHelper.readableDatabase.apply {
                    // Get query planner info
                    rawQuery("EXPLAIN QUERY PLAN SELECT * FROM location_points WHERE dutyId = ? ORDER BY timestamp", arrayOf("1")).use { cursor ->
                        val plans = mutableListOf<String>()
                        while (cursor.moveToNext()) {
                            plans.add(cursor.getString(3)) // detail column
                        }
                        queryPlan["location_points_query_plan"] = plans
                    }
                    
                    // Get table info
                    rawQuery("SELECT name, sql FROM sqlite_master WHERE type='table'", null).use { cursor ->
                        val tables = mutableListOf<Map<String, String>>()
                        while (cursor.moveToNext()) {
                            tables.add(mapOf(
                                "name" to cursor.getString(0),
                                "sql" to (cursor.getString(1) ?: "")
                            ))
                        }
                        queryPlan["tables"] = tables
                    }
                    
                    // Get index info
                    rawQuery("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index'", null).use { cursor ->
                        val indexes = mutableListOf<Map<String, String>>()
                        while (cursor.moveToNext()) {
                            indexes.add(mapOf(
                                "name" to cursor.getString(0),
                                "table" to cursor.getString(1),
                                "sql" to (cursor.getString(2) ?: "")
                            ))
                        }
                        queryPlan["indexes"] = indexes
                    }
                }
                
                queryPlan
            } catch (e: Exception) {
                logger.e(TAG, "Error analyzing query performance", throwable = e)
                mapOf("error" to e.message)
            }
        }
    }
    
    fun shutdown() {
        logger.i(TAG, "Database performance optimizer shutting down")
        optimizationScope.cancel()
    }
}