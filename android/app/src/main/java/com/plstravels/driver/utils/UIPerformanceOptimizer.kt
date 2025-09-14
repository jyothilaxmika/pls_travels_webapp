package com.plstravels.driver.utils

import androidx.compose.runtime.*
import androidx.compose.ui.graphics.toArgb
import androidx.lifecycle.DefaultLifecycleObserver
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.ProcessLifecycleOwner
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import androidx.compose.runtime.snapshots.SnapshotStateMap
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicLong
import javax.inject.Inject
import javax.inject.Singleton

/**
 * UI performance optimizer for Compose applications
 * Handles lazy loading, state management optimization, and UI responsiveness
 */
@Singleton
class UIPerformanceOptimizer @Inject constructor(
    private val logger: ProdLogger,
    private val memoryManager: MemoryManager
) : DefaultLifecycleObserver, MemoryManager.MemoryListener {
    
    private val optimizationScope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    
    // Performance tracking
    private val recompositionTracker = RecompositionTracker()
    private val stateOptimizer = StateOptimizer()
    private val lazyLoadingManager = LazyLoadingManager()
    
    // Configuration
    private var optimizationLevel = OptimizationLevel.BALANCED
    private var isEnabled = true
    
    companion object {
        private const val TAG = "UIPerformanceOptimizer"
        private const val RECOMPOSITION_THRESHOLD = 10
        private const val STATE_CLEANUP_INTERVAL_MS = 30_000L
    }
    
    enum class OptimizationLevel {
        AGGRESSIVE,    // Maximum optimization, may affect visual quality
        BALANCED,      // Balance between performance and visual quality
        MINIMAL        // Minimal optimization, prioritize visual quality
    }
    
    data class RecompositionInfo(
        val composableName: String,
        val count: AtomicLong = AtomicLong(0),
        val lastRecomposition: AtomicLong = AtomicLong(0),
        val averageInterval: AtomicLong = AtomicLong(0)
    )
    
    /**
     * Tracks recompositions for performance analysis
     */
    class RecompositionTracker {
        private val recompositions = ConcurrentHashMap<String, RecompositionInfo>()
        
        fun trackRecomposition(composableName: String) {
            val info = recompositions.getOrPut(composableName) { RecompositionInfo(composableName) }
            val currentTime = System.currentTimeMillis()
            val lastTime = info.lastRecomposition.getAndSet(currentTime)
            
            info.count.incrementAndGet()
            
            if (lastTime > 0) {
                val interval = currentTime - lastTime
                val currentAvg = info.averageInterval.get()
                val newAvg = if (currentAvg == 0L) interval else (currentAvg + interval) / 2
                info.averageInterval.set(newAvg)
            }
        }
        
        fun getRecompositionInfo(): Map<String, RecompositionInfo> = recompositions.toMap()
        
        fun getExcessiveRecompositions(threshold: Long = RECOMPOSITION_THRESHOLD.toLong()): List<RecompositionInfo> {
            return recompositions.values.filter { it.count.get() > threshold }
        }
        
        fun reset() {
            recompositions.clear()
        }
    }
    
    /**
     * Optimizes state management to reduce unnecessary recompositions
     */
    class StateOptimizer {
        private val stateHolders = ConcurrentHashMap<String, Any>()
        private var lastCleanup = System.currentTimeMillis()
        
        @Composable
        fun <T> optimizedState(
            key: String,
            initialValue: T,
            policy: SnapshotMutationPolicy<T> = structuralEqualityPolicy()
        ): MutableState<T> {
            return remember(key) {
                mutableStateOf(initialValue, policy)
            }
        }
        
        @Composable
        fun <T> derivedStateOptimized(
            key: String,
            vararg inputs: Any?,
            calculation: () -> T
        ): State<T> {
            return remember(key, *inputs) {
                derivedStateOf(calculation)
            }
        }
        
        @Composable
        fun <T> stableCollectionState(
            collection: List<T>,
            keySelector: (T) -> Any = { it.hashCode() }
        ): State<List<T>> {
            return remember {
                derivedStateOf {
                    collection.toList() // Create immutable copy
                }
            }
        }
        
        fun shouldCleanup(): Boolean {
            val now = System.currentTimeMillis()
            return (now - lastCleanup) > STATE_CLEANUP_INTERVAL_MS
        }
        
        fun performCleanup() {
            lastCleanup = System.currentTimeMillis()
            // Remove unused state holders
            stateHolders.clear()
        }
    }
    
    /**
     * Manages lazy loading for better performance
     */
    class LazyLoadingManager {
        private val loadingStates = SnapshotStateMap<String, LoadingState>()
        
        data class LoadingState(
            val isLoading: Boolean = false,
            val isLoaded: Boolean = false,
            val error: Throwable? = null,
            val lastLoadTime: Long = 0
        )
        
        @Composable
        fun <T> lazyLoadContent(
            key: String,
            threshold: Int = 50, // Load when within 50px of viewport
            content: @Composable () -> T
        ): @Composable () -> T {
            var isVisible by remember { mutableStateOf(false) }
            
            // Initialize state if not present
            if (!loadingStates.containsKey(key)) {
                loadingStates[key] = LoadingState()
            }
            
            // Observe the loading state from the SnapshotStateMap
            val currentLoadingState by remember(key) {
                derivedStateOf { loadingStates[key] ?: LoadingState() }
            }
            
            // Auto-trigger visibility when loading state is marked as loading
            LaunchedEffect(currentLoadingState.isLoading) {
                if (currentLoadingState.isLoading) {
                    isVisible = true
                }
            }
            
            return {
                if (isVisible || currentLoadingState.isLoaded) {
                    content()
                    // Update to loaded state if not already loaded
                    if (!currentLoadingState.isLoaded) {
                        loadingStates[key] = currentLoadingState.copy(isLoaded = true)
                    }
                } else {
                    // Placeholder or loading indicator
                }
            }
        }
        
        fun markAsVisible(key: String) {
            val currentState = loadingStates[key] ?: LoadingState()
            loadingStates[key] = currentState.copy(isLoading = true)
        }
        
        fun markAsLoaded(key: String) {
            val currentState = loadingStates[key] ?: LoadingState()
            loadingStates[key] = currentState.copy(
                isLoading = false,
                isLoaded = true,
                lastLoadTime = System.currentTimeMillis()
            )
        }
        
        fun markAsError(key: String, error: Throwable) {
            val currentState = loadingStates[key] ?: LoadingState()
            loadingStates[key] = currentState.copy(
                isLoading = false,
                error = error
            )
        }
        
        fun clearCache() {
            loadingStates.clear()
        }
    }
    
    fun initialize() {
        ProcessLifecycleOwner.get().lifecycle.addObserver(this)
        memoryManager.addMemoryListener(this)
        startOptimizationTasks()
        logger.i(TAG, "UI performance optimizer initialized")
    }
    
    private fun startOptimizationTasks() {
        optimizationScope.launch {
            while (isActive && isEnabled) {
                try {
                    performPeriodicOptimizations()
                    delay(STATE_CLEANUP_INTERVAL_MS)
                } catch (e: Exception) {
                    logger.e(TAG, "Error during periodic optimization", throwable = e)
                    delay(STATE_CLEANUP_INTERVAL_MS * 2)
                }
            }
        }
    }
    
    private suspend fun performPeriodicOptimizations() {
        withContext(Dispatchers.Main) {
            // Check for excessive recompositions
            val excessiveRecompositions = recompositionTracker.getExcessiveRecompositions()
            if (excessiveRecompositions.isNotEmpty()) {
                logger.w(TAG, "Excessive recompositions detected", mapOf(
                    "count" to excessiveRecompositions.size.toString(),
                    "composables" to excessiveRecompositions.joinToString { it.composableName }
                ))
            }
            
            // Clean up state if needed
            if (stateOptimizer.shouldCleanup()) {
                stateOptimizer.performCleanup()
                logger.d(TAG, "State cleanup performed")
            }
            
            // Memory optimization based on current level
            when (optimizationLevel) {
                OptimizationLevel.AGGRESSIVE -> {
                    lazyLoadingManager.clearCache()
                    recompositionTracker.reset()
                }
                OptimizationLevel.BALANCED -> {
                    // Selective cleanup
                }
                OptimizationLevel.MINIMAL -> {
                    // Minimal cleanup
                }
            }
        }
    }
    
    /**
     * Composable for tracking recompositions
     */
    @Composable
    fun RecompositionTracker(
        name: String,
        content: @Composable () -> Unit
    ) {
        SideEffect {
            recompositionTracker.trackRecomposition(name)
        }
        content()
    }
    
    /**
     * Optimized LazyColumn item with automatic lazy loading
     */
    @Composable
    fun <T> OptimizedLazyItem(
        item: T,
        key: String,
        content: @Composable (T) -> Unit
    ) {
        val lazyContent = lazyLoadingManager.lazyLoadContent(key) {
            content(item)
        }
        
        DisposableEffect(key) {
            lazyLoadingManager.markAsVisible(key)
            onDispose {
                // Cleanup if needed
            }
        }
        
        lazyContent()
    }
    
    /**
     * Memory-efficient image loading for lists
     */
    @Composable
    fun OptimizedAsyncImage(
        imageUrl: String,
        contentDescription: String?,
        modifier: androidx.compose.ui.Modifier = androidx.compose.ui.Modifier,
        placeholder: @Composable (() -> Unit)? = null,
        error: @Composable (() -> Unit)? = null
    ) {
        // Use Coil with optimizations
        val imageRequest = remember(imageUrl) {
            coil.request.ImageRequest.Builder(androidx.compose.ui.platform.LocalContext.current)
                .data(imageUrl)
                .memoryCachePolicy(coil.request.CachePolicy.ENABLED)
                .diskCachePolicy(coil.request.CachePolicy.ENABLED)
                .build()
        }
        
        // Implementation would use Coil's AsyncImage with the optimized request
        // This is a placeholder for the actual implementation
    }
    
    /**
     * Optimized state flow collection for Compose
     */
    @Composable
    fun <T> StateFlow<T>.collectAsStateOptimized(): State<T> {
        return collectAsState(context = Dispatchers.Main.immediate)
    }
    
    /**
     * Debounced state for reducing frequent updates
     */
    @Composable
    fun <T> debouncedState(
        value: T,
        delayMillis: Long = 300
    ): State<T> {
        val debouncedValue = remember { mutableStateOf(value) }
        
        LaunchedEffect(value) {
            delay(delayMillis)
            debouncedValue.value = value
        }
        
        return debouncedValue
    }
    
    /**
     * Stable wrapper for unstable parameters
     */
    @Stable
    data class StableWrapper<T>(val value: T)
    
    @Composable
    fun <T> rememberStable(value: T): StableWrapper<T> {
        return remember(value) { StableWrapper(value) }
    }
    
    /**
     * Performance monitoring for Compose functions
     */
    @Composable
    inline fun <T> performanceTraced(
        name: String,
        crossinline content: @Composable () -> T
    ): T {
        return androidx.tracing.trace(name) {
            content()
        }
    }
    
    /**
     * Get performance metrics
     */
    fun getPerformanceMetrics(): Map<String, Any> {
        val recompositionInfo = recompositionTracker.getRecompositionInfo()
        val excessiveRecompositions = recompositionTracker.getExcessiveRecompositions()
        
        return mapOf(
            "total_tracked_composables" to recompositionInfo.size,
            "excessive_recompositions" to excessiveRecompositions.size,
            "total_recompositions" to recompositionInfo.values.sumOf { it.count.get() },
            "optimization_level" to optimizationLevel.name,
            "is_enabled" to isEnabled
        )
    }
    
    /**
     * Set optimization level based on device performance
     */
    fun setOptimizationLevel(level: OptimizationLevel) {
        optimizationLevel = level
        logger.i(TAG, "UI optimization level changed to: $level")
        
        when (level) {
            OptimizationLevel.AGGRESSIVE -> {
                // Enable all optimizations
                optimizationScope.launch {
                    performPeriodicOptimizations()
                }
            }
            OptimizationLevel.BALANCED -> {
                // Balanced approach
            }
            OptimizationLevel.MINIMAL -> {
                // Minimal optimizations
            }
        }
    }
    
    /**
     * Enable or disable optimizations
     */
    fun setEnabled(enabled: Boolean) {
        isEnabled = enabled
        logger.i(TAG, "UI optimization ${if (enabled) "enabled" else "disabled"}")
    }
    
    // MemoryManager.MemoryListener implementation
    override fun onMemoryWarning(level: MemoryManager.MemoryLevel) {
        when (level) {
            MemoryManager.MemoryLevel.CRITICAL -> {
                setOptimizationLevel(OptimizationLevel.AGGRESSIVE)
                optimizationScope.launch {
                    lazyLoadingManager.clearCache()
                    recompositionTracker.reset()
                    stateOptimizer.performCleanup()
                }
            }
            MemoryManager.MemoryLevel.LOW -> {
                if (optimizationLevel == OptimizationLevel.MINIMAL) {
                    setOptimizationLevel(OptimizationLevel.BALANCED)
                }
            }
            else -> {
                // No immediate action for normal memory levels
            }
        }
    }
    
    override fun onMemoryOptimizationRecommended() {
        optimizationScope.launch {
            stateOptimizer.performCleanup()
        }
    }
    
    override fun onStart(owner: LifecycleOwner) {
        logger.d(TAG, "App in foreground - full UI optimization enabled")
        setEnabled(true)
    }
    
    override fun onStop(owner: LifecycleOwner) {
        logger.d(TAG, "App in background - reducing UI optimizations")
        optimizationScope.launch {
            performPeriodicOptimizations()
        }
    }
    
    fun shutdown() {
        logger.i(TAG, "UI performance optimizer shutting down")
        setEnabled(false)
        optimizationScope.cancel()
        ProcessLifecycleOwner.get().lifecycle.removeObserver(this)
        memoryManager.removeMemoryListener(this)
        
        // Clean up all state
        recompositionTracker.reset()
        stateOptimizer.performCleanup()
        lazyLoadingManager.clearCache()
    }
}