package com.plstravels.driver.utils

import android.app.ActivityManager
import android.content.Context
import android.os.Build
import android.os.Handler
import android.os.Looper
import androidx.lifecycle.DefaultLifecycleObserver
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.ProcessLifecycleOwner
import androidx.tracing.trace
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.*
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicLong
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Performance monitoring system for tracking app performance metrics
 */
@Singleton
class PerformanceMonitor @Inject constructor(
    @ApplicationContext private val context: Context,
    private val logger: ProdLogger,
    private val memoryManager: MemoryManager
) : DefaultLifecycleObserver {
    
    private val monitoringScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val mainHandler = Handler(Looper.getMainLooper())
    
    // Performance metrics
    private val operationMetrics = ConcurrentHashMap<String, OperationMetrics>()
    private val frameMetrics = FrameMetrics()
    private val networkMetrics = NetworkMetrics()
    
    // Monitoring state
    private var isMonitoring = false
    private var monitoringStartTime = 0L
    
    companion object {
        private const val TAG = "PerformanceMonitor"
        private const val MONITORING_INTERVAL_MS = 5000L // 5 seconds
        private const val SLOW_OPERATION_THRESHOLD_MS = 1000L
        private const val ANR_THRESHOLD_MS = 5000L
        private const val MAX_METRICS_ENTRIES = 1000
    }
    
    data class OperationMetrics(
        val name: String,
        val totalCount: AtomicLong = AtomicLong(0),
        val totalDuration: AtomicLong = AtomicLong(0),
        val slowOperations: AtomicLong = AtomicLong(0),
        val errorCount: AtomicLong = AtomicLong(0),
        val lastExecutionTime: AtomicLong = AtomicLong(0)
    ) {
        fun getAverageDuration(): Double {
            val count = totalCount.get()
            return if (count > 0) totalDuration.get().toDouble() / count else 0.0
        }
        
        fun getErrorRate(): Double {
            val count = totalCount.get()
            return if (count > 0) errorCount.get().toDouble() / count else 0.0
        }
    }
    
    data class FrameMetrics(
        val totalFrames: AtomicLong = AtomicLong(0),
        val droppedFrames: AtomicLong = AtomicLong(0),
        val slowFrames: AtomicLong = AtomicLong(0),
        val jankyFrames: AtomicLong = AtomicLong(0)
    ) {
        fun getDroppedFrameRate(): Double {
            val total = totalFrames.get()
            return if (total > 0) droppedFrames.get().toDouble() / total else 0.0
        }
    }
    
    data class NetworkMetrics(
        val totalRequests: AtomicLong = AtomicLong(0),
        val successfulRequests: AtomicLong = AtomicLong(0),
        val failedRequests: AtomicLong = AtomicLong(0),
        val totalResponseTime: AtomicLong = AtomicLong(0),
        val slowRequests: AtomicLong = AtomicLong(0)
    ) {
        fun getSuccessRate(): Double {
            val total = totalRequests.get()
            return if (total > 0) successfulRequests.get().toDouble() / total else 0.0
        }
        
        fun getAverageResponseTime(): Double {
            val total = totalRequests.get()
            return if (total > 0) totalResponseTime.get().toDouble() / total else 0.0
        }
    }
    
    data class PerformanceSnapshot(
        val timestamp: Long,
        val memoryInfo: MemoryManager.MemoryInfo,
        val operationMetrics: Map<String, OperationMetrics>,
        val frameMetrics: FrameMetrics,
        val networkMetrics: NetworkMetrics,
        val cpuUsage: Double,
        val batteryLevel: Int
    )
    
    fun initialize() {
        ProcessLifecycleOwner.get().lifecycle.addObserver(this)
        startMonitoring()
        logger.i(TAG, "Performance monitor initialized")
    }
    
    private fun startMonitoring() {
        if (isMonitoring) return
        
        isMonitoring = true
        monitoringStartTime = System.currentTimeMillis()
        
        monitoringScope.launch {
            while (isActive && isMonitoring) {
                try {
                    collectPerformanceMetrics()
                    cleanupOldMetrics()
                    delay(MONITORING_INTERVAL_MS)
                } catch (e: Exception) {
                    logger.e(TAG, "Error during performance monitoring", throwable = e)
                    delay(MONITORING_INTERVAL_MS * 2) // Backoff on error
                }
            }
        }
        
        logger.i(TAG, "Performance monitoring started")
    }
    
    private suspend fun collectPerformanceMetrics() {
        withContext(Dispatchers.IO) {
            try {
                val snapshot = createPerformanceSnapshot()
                analyzePerformance(snapshot)
                
                // Log performance summary periodically
                if ((System.currentTimeMillis() - monitoringStartTime) % (60_000L) == 0L) {
                    logPerformanceSummary(snapshot)
                }
                
            } catch (e: Exception) {
                logger.e(TAG, "Error collecting performance metrics", throwable = e)
            }
        }
    }
    
    private fun createPerformanceSnapshot(): PerformanceSnapshot {
        return PerformanceSnapshot(
            timestamp = System.currentTimeMillis(),
            memoryInfo = memoryManager.getCurrentMemoryInfo(),
            operationMetrics = operationMetrics.toMap(),
            frameMetrics = frameMetrics,
            networkMetrics = networkMetrics,
            cpuUsage = getCpuUsage(),
            batteryLevel = getBatteryLevel()
        )
    }
    
    private fun analyzePerformance(snapshot: PerformanceSnapshot) {
        // Analyze memory
        if (snapshot.memoryInfo.level == MemoryManager.MemoryLevel.CRITICAL) {
            logger.w(TAG, "Critical memory detected in performance analysis")
        }
        
        // Analyze slow operations
        snapshot.operationMetrics.values.forEach { metrics ->
            val errorRate = metrics.getErrorRate()
            val avgDuration = metrics.getAverageDuration()
            
            if (errorRate > 0.1) { // 10% error rate
                logger.w(TAG, "High error rate detected", mapOf(
                    "operation" to metrics.name,
                    "error_rate" to String.format("%.2f", errorRate * 100)
                ))
            }
            
            if (avgDuration > SLOW_OPERATION_THRESHOLD_MS) {
                logger.w(TAG, "Slow operation detected", mapOf(
                    "operation" to metrics.name,
                    "avg_duration_ms" to avgDuration.toString()
                ))
            }
        }
        
        // Analyze frame performance
        val frameDropRate = snapshot.frameMetrics.getDroppedFrameRate()
        if (frameDropRate > 0.05) { // 5% dropped frames
            logger.w(TAG, "High frame drop rate detected", mapOf(
                "drop_rate" to String.format("%.2f", frameDropRate * 100)
            ))
        }
        
        // Analyze network performance
        val networkSuccessRate = snapshot.networkMetrics.getSuccessRate()
        if (networkSuccessRate < 0.95) { // Less than 95% success rate
            logger.w(TAG, "Low network success rate detected", mapOf(
                "success_rate" to String.format("%.2f", networkSuccessRate * 100)
            ))
        }
    }
    
    /**
     * Track operation performance
     */
    inline fun <T> trackOperation(
        operationName: String,
        operation: () -> T
    ): T {
        return trace(operationName) {
            val startTime = System.currentTimeMillis()
            val metrics = operationMetrics.getOrPut(operationName) { 
                OperationMetrics(operationName) 
            }
            
            try {
                val result = operation()
                
                val duration = System.currentTimeMillis() - startTime
                updateOperationMetrics(metrics, duration, false)
                
                result
            } catch (e: Exception) {
                val duration = System.currentTimeMillis() - startTime
                updateOperationMetrics(metrics, duration, true)
                
                logger.e(TAG, "Operation failed: $operationName", mapOf(
                    "duration_ms" to duration.toString()
                ), e)
                
                throw e
            }
        }
    }
    
    /**
     * Track async operation performance
     */
    suspend inline fun <T> trackAsyncOperation(
        operationName: String,
        crossinline operation: suspend () -> T
    ): T {
        return trace(operationName) {
            val startTime = System.currentTimeMillis()
            val metrics = operationMetrics.getOrPut(operationName) { 
                OperationMetrics(operationName) 
            }
            
            try {
                val result = operation()
                
                val duration = System.currentTimeMillis() - startTime
                updateOperationMetrics(metrics, duration, false)
                
                result
            } catch (e: Exception) {
                val duration = System.currentTimeMillis() - startTime
                updateOperationMetrics(metrics, duration, true)
                
                logger.e(TAG, "Async operation failed: $operationName", mapOf(
                    "duration_ms" to duration.toString()
                ), e)
                
                throw e
            }
        }
    }
    
    private fun updateOperationMetrics(metrics: OperationMetrics, duration: Long, isError: Boolean) {
        metrics.totalCount.incrementAndGet()
        metrics.totalDuration.addAndGet(duration)
        metrics.lastExecutionTime.set(System.currentTimeMillis())
        
        if (isError) {
            metrics.errorCount.incrementAndGet()
        }
        
        if (duration > SLOW_OPERATION_THRESHOLD_MS) {
            metrics.slowOperations.incrementAndGet()
        }
    }
    
    /**
     * Track network request performance
     */
    fun trackNetworkRequest(duration: Long, isSuccess: Boolean) {
        networkMetrics.totalRequests.incrementAndGet()
        networkMetrics.totalResponseTime.addAndGet(duration)
        
        if (isSuccess) {
            networkMetrics.successfulRequests.incrementAndGet()
        } else {
            networkMetrics.failedRequests.incrementAndGet()
        }
        
        if (duration > 5000) { // 5 seconds threshold for slow requests
            networkMetrics.slowRequests.incrementAndGet()
        }
    }
    
    /**
     * Track frame rendering performance
     */
    fun trackFrameMetrics(totalFrames: Long, droppedFrames: Long) {
        frameMetrics.totalFrames.addAndGet(totalFrames)
        frameMetrics.droppedFrames.addAndGet(droppedFrames)
        
        // Detect janky frames (dropped frames that could cause visible stuttering)
        if (droppedFrames > 2) {
            frameMetrics.jankyFrames.addAndGet(droppedFrames)
        }
    }
    
    /**
     * Get current performance snapshot
     */
    fun getCurrentSnapshot(): PerformanceSnapshot {
        return createPerformanceSnapshot()
    }
    
    /**
     * Get operation metrics for specific operation
     */
    fun getOperationMetrics(operationName: String): OperationMetrics? {
        return operationMetrics[operationName]
    }
    
    /**
     * Get all operation metrics
     */
    fun getAllOperationMetrics(): Map<String, OperationMetrics> {
        return operationMetrics.toMap()
    }
    
    private fun cleanupOldMetrics() {
        if (operationMetrics.size > MAX_METRICS_ENTRIES) {
            val oldestEntries = operationMetrics.entries
                .sortedBy { it.value.lastExecutionTime.get() }
                .take(operationMetrics.size - MAX_METRICS_ENTRIES + 100) // Clean extra entries
            
            oldestEntries.forEach { entry ->
                operationMetrics.remove(entry.key)
            }
            
            logger.d(TAG, "Cleaned up ${oldestEntries.size} old metric entries")
        }
    }
    
    private fun logPerformanceSummary(snapshot: PerformanceSnapshot) {
        val summary = mapOf(
            "memory_usage_mb" to (snapshot.memoryInfo.usedHeap / 1024 / 1024).toString(),
            "memory_percentage" to String.format("%.1f", snapshot.memoryInfo.usedPercentage * 100),
            "total_operations" to snapshot.operationMetrics.size.toString(),
            "frame_drop_rate" to String.format("%.2f", snapshot.frameMetrics.getDroppedFrameRate() * 100),
            "network_success_rate" to String.format("%.2f", snapshot.networkMetrics.getSuccessRate() * 100),
            "cpu_usage" to String.format("%.1f", snapshot.cpuUsage),
            "battery_level" to snapshot.batteryLevel.toString()
        )
        
        logger.i(TAG, "Performance summary", summary)
    }
    
    private fun getCpuUsage(): Double {
        return try {
            val activityManager = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
            val memInfo = ActivityManager.MemoryInfo()
            activityManager.getMemoryInfo(memInfo)
            
            // This is a simplified CPU usage calculation
            // For production, consider using more sophisticated methods
            val loadAverage = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                Runtime.getRuntime().availableProcessors().toDouble()
            } else {
                1.0
            }
            
            Math.min(100.0, loadAverage * 10) // Simplified calculation
        } catch (e: Exception) {
            0.0
        }
    }
    
    private fun getBatteryLevel(): Int {
        return try {
            val batteryManager = context.getSystemService(Context.BATTERY_SERVICE) as android.os.BatteryManager
            batteryManager.getIntProperty(android.os.BatteryManager.BATTERY_PROPERTY_CAPACITY)
        } catch (e: Exception) {
            -1
        }
    }
    
    override fun onStart(owner: LifecycleOwner) {
        logger.d(TAG, "App moved to foreground - resuming detailed monitoring")
    }
    
    override fun onStop(owner: LifecycleOwner) {
        logger.d(TAG, "App moved to background - reducing monitoring frequency")
        logPerformanceSummary(getCurrentSnapshot())
    }
    
    fun stopMonitoring() {
        isMonitoring = false
        logger.i(TAG, "Performance monitoring stopped")
    }
    
    fun shutdown() {
        logger.i(TAG, "Performance monitor shutting down")
        stopMonitoring()
        monitoringScope.cancel()
        ProcessLifecycleOwner.get().lifecycle.removeObserver(this)
        operationMetrics.clear()
    }
}