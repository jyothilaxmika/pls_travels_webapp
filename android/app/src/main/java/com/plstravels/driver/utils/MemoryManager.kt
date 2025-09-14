package com.plstravels.driver.utils

import android.app.ActivityManager
import android.content.Context
import android.os.Debug
import android.util.Log
import androidx.lifecycle.DefaultLifecycleObserver
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.ProcessLifecycleOwner
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.*
import java.lang.ref.WeakReference
import java.util.concurrent.atomic.AtomicLong
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Memory management utilities for performance optimization
 * Monitors memory usage, detects leaks, and provides memory cleanup utilities
 */
@Singleton
class MemoryManager @Inject constructor(
    @ApplicationContext private val context: Context,
    private val logger: ProdLogger
) : DefaultLifecycleObserver {
    
    private val activityManager = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
    private val managementScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    
    // Memory tracking
    private var memoryThresholds = MemoryThresholds()
    private val lastGcTime = AtomicLong(0)
    private val gcCallCount = AtomicLong(0)
    
    // Weak references for tracking objects
    private val trackedObjects = mutableSetOf<WeakReference<Any>>()
    private val memoryListeners = mutableSetOf<MemoryListener>()
    
    companion object {
        private const val TAG = "MemoryManager"
        private const val GC_COOLDOWN_MS = 10_000L // 10 seconds between GC calls
        private const val MEMORY_CHECK_INTERVAL_MS = 30_000L // 30 seconds
        private const val LOW_MEMORY_THRESHOLD_PERCENTAGE = 0.85f
        private const val CRITICAL_MEMORY_THRESHOLD_PERCENTAGE = 0.95f
    }
    
    data class MemoryThresholds(
        val lowMemoryThreshold: Long = 0,
        val criticalMemoryThreshold: Long = 0,
        val maxHeapSize: Long = 0
    )
    
    interface MemoryListener {
        fun onMemoryWarning(level: MemoryLevel)
        fun onMemoryOptimizationRecommended()
    }
    
    enum class MemoryLevel {
        NORMAL, LOW, CRITICAL, OUT_OF_MEMORY
    }
    
    data class MemoryInfo(
        val usedHeap: Long,
        val maxHeap: Long,
        val freeHeap: Long,
        val usedPercentage: Float,
        val level: MemoryLevel,
        val nativeHeap: Long,
        val availableSystemMemory: Long
    )
    
    fun initialize() {
        ProcessLifecycleOwner.get().lifecycle.addObserver(this)
        calculateMemoryThresholds()
        startMemoryMonitoring()
        logger.i(TAG, "Memory manager initialized", getMemorySnapshot())
    }
    
    private fun calculateMemoryThresholds() {
        val memInfo = ActivityManager.MemoryInfo()
        activityManager.getMemoryInfo(memInfo)
        
        val runtime = Runtime.getRuntime()
        val maxHeap = runtime.maxMemory()
        
        memoryThresholds = memoryThresholds.copy(
            lowMemoryThreshold = (maxHeap * LOW_MEMORY_THRESHOLD_PERCENTAGE).toLong(),
            criticalMemoryThreshold = (maxHeap * CRITICAL_MEMORY_THRESHOLD_PERCENTAGE).toLong(),
            maxHeapSize = maxHeap
        )
    }
    
    private fun startMemoryMonitoring() {
        managementScope.launch {
            while (isActive) {
                try {
                    val memoryInfo = getCurrentMemoryInfo()
                    checkMemoryLevels(memoryInfo)
                    cleanupWeakReferences()
                    
                    delay(MEMORY_CHECK_INTERVAL_MS)
                } catch (e: Exception) {
                    logger.e(TAG, "Error during memory monitoring", throwable = e)
                    delay(MEMORY_CHECK_INTERVAL_MS * 2) // Backoff on error
                }
            }
        }
    }
    
    /**
     * Get current memory information
     */
    fun getCurrentMemoryInfo(): MemoryInfo {
        val runtime = Runtime.getRuntime()
        val maxHeap = runtime.maxMemory()
        val totalHeap = runtime.totalMemory()
        val freeHeap = runtime.freeMemory()
        val usedHeap = totalHeap - freeHeap
        val usedPercentage = (usedHeap.toFloat() / maxHeap.toFloat())
        
        val memInfo = ActivityManager.MemoryInfo()
        activityManager.getMemoryInfo(memInfo)
        
        val level = when {
            usedPercentage >= CRITICAL_MEMORY_THRESHOLD_PERCENTAGE -> MemoryLevel.CRITICAL
            usedPercentage >= LOW_MEMORY_THRESHOLD_PERCENTAGE -> MemoryLevel.LOW
            memInfo.lowMemory -> MemoryLevel.LOW
            else -> MemoryLevel.NORMAL
        }
        
        return MemoryInfo(
            usedHeap = usedHeap,
            maxHeap = maxHeap,
            freeHeap = maxHeap - usedHeap,
            usedPercentage = usedPercentage,
            level = level,
            nativeHeap = Debug.getNativeHeapAllocatedSize(),
            availableSystemMemory = memInfo.availMem
        )
    }
    
    private fun checkMemoryLevels(memoryInfo: MemoryInfo) {
        when (memoryInfo.level) {
            MemoryLevel.CRITICAL -> {
                logger.w(TAG, "Critical memory usage detected", mapOf(
                    "used_percentage" to memoryInfo.usedPercentage.toString(),
                    "used_heap_mb" to (memoryInfo.usedHeap / 1024 / 1024).toString()
                ))
                notifyMemoryListeners(MemoryLevel.CRITICAL)
                performAggressiveCleanup()
            }
            MemoryLevel.LOW -> {
                logger.w(TAG, "Low memory warning", mapOf(
                    "used_percentage" to memoryInfo.usedPercentage.toString()
                ))
                notifyMemoryListeners(MemoryLevel.LOW)
                performGentleCleanup()
            }
            MemoryLevel.NORMAL -> {
                // Routine maintenance
                if (shouldPerformRoutineCleanup()) {
                    performRoutineCleanup()
                }
            }
            MemoryLevel.OUT_OF_MEMORY -> {
                logger.e(TAG, "Out of memory condition")
                notifyMemoryListeners(MemoryLevel.OUT_OF_MEMORY)
                performEmergencyCleanup()
            }
        }
    }
    
    /**
     * Request garbage collection with cooldown
     */
    fun requestGarbageCollection(force: Boolean = false): Boolean {
        val currentTime = System.currentTimeMillis()
        val lastGc = lastGcTime.get()
        
        if (!force && (currentTime - lastGc) < GC_COOLDOWN_MS) {
            logger.d(TAG, "GC request ignored due to cooldown")
            return false
        }
        
        if (lastGcTime.compareAndSet(lastGc, currentTime)) {
            gcCallCount.incrementAndGet()
            System.gc()
            logger.i(TAG, "Garbage collection requested", mapOf(
                "gc_count" to gcCallCount.get().toString(),
                "force" to force.toString()
            ))
            return true
        }
        
        return false
    }
    
    /**
     * Track object for memory leak detection
     */
    fun trackObject(obj: Any, tag: String? = null) {
        synchronized(trackedObjects) {
            trackedObjects.add(WeakReference(obj))
            logger.d(TAG, "Object tracked: ${tag ?: obj.javaClass.simpleName}")
        }
    }
    
    /**
     * Add memory listener for memory events
     */
    fun addMemoryListener(listener: MemoryListener) {
        synchronized(memoryListeners) {
            memoryListeners.add(listener)
        }
    }
    
    /**
     * Remove memory listener
     */
    fun removeMemoryListener(listener: MemoryListener) {
        synchronized(memoryListeners) {
            memoryListeners.remove(listener)
        }
    }
    
    private fun notifyMemoryListeners(level: MemoryLevel) {
        synchronized(memoryListeners) {
            memoryListeners.forEach { listener ->
                try {
                    listener.onMemoryWarning(level)
                } catch (e: Exception) {
                    logger.e(TAG, "Error notifying memory listener", throwable = e)
                }
            }
        }
    }
    
    private fun cleanupWeakReferences() {
        synchronized(trackedObjects) {
            val iterator = trackedObjects.iterator()
            var cleanedCount = 0
            
            while (iterator.hasNext()) {
                val ref = iterator.next()
                if (ref.get() == null) {
                    iterator.remove()
                    cleanedCount++
                }
            }
            
            if (cleanedCount > 0) {
                logger.d(TAG, "Cleaned $cleanedCount weak references")
            }
        }
    }
    
    private fun shouldPerformRoutineCleanup(): Boolean {
        val memoryInfo = getCurrentMemoryInfo()
        return memoryInfo.usedPercentage > 0.7f // 70% threshold for routine cleanup
    }
    
    private fun performRoutineCleanup() {
        logger.d(TAG, "Performing routine memory cleanup")
        cleanupWeakReferences()
        
        // Suggest optimization to listeners
        synchronized(memoryListeners) {
            memoryListeners.forEach { listener ->
                try {
                    listener.onMemoryOptimizationRecommended()
                } catch (e: Exception) {
                    logger.e(TAG, "Error during routine cleanup notification", throwable = e)
                }
            }
        }
    }
    
    private fun performGentleCleanup() {
        logger.i(TAG, "Performing gentle memory cleanup")
        cleanupWeakReferences()
        // Note: No GC call here to prevent UI jank - GC is only triggered at CRITICAL level
    }
    
    private fun performAggressiveCleanup() {
        logger.w(TAG, "Performing aggressive memory cleanup")
        cleanupWeakReferences()
        requestGarbageCollection(force = true)
        
        // Additional cleanup can be performed here
        // e.g., clearing caches, releasing optional resources
    }
    
    private fun performEmergencyCleanup() {
        logger.e(TAG, "Performing emergency memory cleanup")
        cleanupWeakReferences()
        requestGarbageCollection(force = true)
        
        // Emergency measures
        // Clear all possible caches and release resources
    }
    
    private fun getMemorySnapshot(): Map<String, String> {
        val memoryInfo = getCurrentMemoryInfo()
        return mapOf(
            "used_heap_mb" to (memoryInfo.usedHeap / 1024 / 1024).toString(),
            "max_heap_mb" to (memoryInfo.maxHeap / 1024 / 1024).toString(),
            "used_percentage" to String.format("%.1f", memoryInfo.usedPercentage * 100),
            "memory_level" to memoryInfo.level.name,
            "native_heap_mb" to (memoryInfo.nativeHeap / 1024 / 1024).toString(),
            "available_system_mb" to (memoryInfo.availableSystemMemory / 1024 / 1024).toString()
        )
    }
    
    override fun onStart(owner: LifecycleOwner) {
        logger.d(TAG, "App moved to foreground")
    }
    
    override fun onStop(owner: LifecycleOwner) {
        logger.d(TAG, "App moved to background - performing cleanup")
        performGentleCleanup()
    }
    
    fun shutdown() {
        logger.i(TAG, "Memory manager shutting down")
        managementScope.cancel()
        ProcessLifecycleOwner.get().lifecycle.removeObserver(this)
        
        synchronized(memoryListeners) {
            memoryListeners.clear()
        }
        
        synchronized(trackedObjects) {
            trackedObjects.clear()
        }
    }
}