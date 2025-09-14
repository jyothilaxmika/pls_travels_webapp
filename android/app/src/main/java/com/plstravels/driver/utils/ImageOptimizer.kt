package com.plstravels.driver.utils

import android.content.Context
import android.graphics.*
import android.media.ExifInterface
import android.net.Uri
import android.util.LruCache
import androidx.core.graphics.drawable.toBitmap
import coil.ImageLoader
import coil.decode.DecodeResult
import coil.decode.Decoder
import coil.fetch.SourceResult
import coil.memory.MemoryCache
import coil.request.ImageRequest
import coil.request.Options
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.*
import java.io.*
import java.util.concurrent.ConcurrentHashMap
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Image optimization and caching manager
 * Handles image compression, resizing, caching, and memory management
 */
@Singleton
class ImageOptimizer @Inject constructor(
    @ApplicationContext private val context: Context,
    private val logger: ProdLogger,
    private val memoryManager: MemoryManager
) : MemoryManager.MemoryListener {
    
    private val optimizationScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    
    // Image cache
    private val memoryCache = createMemoryCache()
    private val diskCache = createDiskCache()
    private val compressionCache = ConcurrentHashMap<String, CompressedImageInfo>()
    
    // Optimization settings
    private var currentOptimizationLevel = OptimizationLevel.BALANCED
    
    companion object {
        private const val TAG = "ImageOptimizer"
        private const val MAX_CACHE_SIZE_MB = 50
        private const val MAX_IMAGE_DIMENSION = 2048
        private const val WEBP_QUALITY = 80
        private const val JPEG_QUALITY = 85
        private const val THUMBNAIL_SIZE = 300
        private const val DISK_CACHE_SIZE = 100L * 1024 * 1024 // 100MB
    }
    
    enum class OptimizationLevel {
        AGGRESSIVE,    // Maximum compression, lowest quality
        BALANCED,      // Balance between quality and size
        QUALITY        // Prioritize quality over size
    }
    
    data class ImageOptimizationConfig(
        val maxWidth: Int = MAX_IMAGE_DIMENSION,
        val maxHeight: Int = MAX_IMAGE_DIMENSION,
        val quality: Int = JPEG_QUALITY,
        val format: Bitmap.CompressFormat = Bitmap.CompressFormat.JPEG,
        val stripExif: Boolean = true,
        val generateThumbnail: Boolean = true
    )
    
    data class CompressedImageInfo(
        val originalSize: Long,
        val compressedSize: Long,
        val compressionRatio: Float,
        val dimensions: Pair<Int, Int>,
        val format: String,
        val timestamp: Long
    )
    
    data class OptimizationResult(
        val optimizedFile: File,
        val thumbnailFile: File?,
        val originalSize: Long,
        val optimizedSize: Long,
        val compressionRatio: Float,
        val processingTime: Long
    )
    
    fun initialize() {
        memoryManager.addMemoryListener(this)
        setupImageLoader()
        logger.i(TAG, "Image optimizer initialized")
    }
    
    private fun createMemoryCache(): LruCache<String, Bitmap> {
        val maxMemory = (Runtime.getRuntime().maxMemory() / 1024).toInt()
        val cacheSize = (maxMemory / 8).coerceAtMost(MAX_CACHE_SIZE_MB * 1024) // 1/8th of max memory or 50MB
        
        return object : LruCache<String, Bitmap>(cacheSize) {
            override fun sizeOf(key: String, bitmap: Bitmap): Int {
                return bitmap.byteCount / 1024 // Size in KB
            }
            
            override fun entryRemoved(evicted: Boolean, key: String, oldValue: Bitmap, newValue: Bitmap?) {
                if (evicted && !oldValue.isRecycled) {
                    logger.d(TAG, "Bitmap evicted from cache: $key")
                }
            }
        }
    }
    
    private fun createDiskCache(): File {
        val cacheDir = File(context.cacheDir, "optimized_images")
        if (!cacheDir.exists()) {
            cacheDir.mkdirs()
        }
        return cacheDir
    }
    
    private fun setupImageLoader() {
        // Configure Coil for optimal performance
        val imageLoader = ImageLoader.Builder(context)
            .memoryCache {
                MemoryCache.Builder(context)
                    .maxSizePercent(0.25) // 25% of max memory
                    .build()
            }
            .diskCache {
                coil.disk.DiskCache.Builder()
                    .directory(createDiskCache())
                    .maxSizeBytes(DISK_CACHE_SIZE)
                    .build()
            }
            .build()
        
        logger.d(TAG, "Image loader configured")
    }
    
    /**
     * Optimize image file for storage and display
     */
    suspend fun optimizeImage(
        inputFile: File,
        outputFile: File? = null,
        config: ImageOptimizationConfig = getDefaultConfig()
    ): OptimizationResult {
        return withContext(Dispatchers.IO) {
            val startTime = System.currentTimeMillis()
            val originalSize = inputFile.length()
            
            try {
                val bitmap = loadAndPreprocessBitmap(inputFile, config)
                    ?: throw IllegalArgumentException("Unable to decode image: ${inputFile.path}")
                
                val finalOutputFile = outputFile ?: createOptimizedFile(inputFile, config.format)
                val thumbnailFile = if (config.generateThumbnail) {
                    createThumbnailFile(inputFile)
                } else null
                
                // Compress main image
                val compressedSize = compressBitmap(bitmap, finalOutputFile, config)
                
                // Generate thumbnail if requested
                thumbnailFile?.let { thumbFile ->
                    generateThumbnail(bitmap, thumbFile, config)
                }
                
                // Clean up bitmap
                if (!bitmap.isRecycled) {
                    bitmap.recycle()
                }
                
                val processingTime = System.currentTimeMillis() - startTime
                val compressionRatio = if (originalSize > 0) compressedSize.toFloat() / originalSize else 1f
                
                // Cache compression info
                val cacheKey = generateCacheKey(inputFile)
                compressionCache[cacheKey] = CompressedImageInfo(
                    originalSize = originalSize,
                    compressedSize = compressedSize,
                    compressionRatio = compressionRatio,
                    dimensions = bitmap.width to bitmap.height,
                    format = config.format.name,
                    timestamp = System.currentTimeMillis()
                )
                
                logger.i(TAG, "Image optimized", mapOf(
                    "original_size_kb" to (originalSize / 1024).toString(),
                    "compressed_size_kb" to (compressedSize / 1024).toString(),
                    "compression_ratio" to String.format("%.2f", compressionRatio),
                    "processing_time_ms" to processingTime.toString()
                ))
                
                OptimizationResult(
                    optimizedFile = finalOutputFile,
                    thumbnailFile = thumbnailFile,
                    originalSize = originalSize,
                    optimizedSize = compressedSize,
                    compressionRatio = compressionRatio,
                    processingTime = processingTime
                )
                
            } catch (e: Exception) {
                logger.e(TAG, "Error optimizing image", mapOf(
                    "input_file" to inputFile.path,
                    "original_size_kb" to (originalSize / 1024).toString()
                ), e)
                throw e
            }
        }
    }
    
    private fun loadAndPreprocessBitmap(inputFile: File, config: ImageOptimizationConfig): Bitmap? {
        val options = BitmapFactory.Options().apply {
            inJustDecodeBounds = true
        }
        
        BitmapFactory.decodeFile(inputFile.path, options)
        
        // Calculate sample size for memory efficiency
        options.inSampleSize = calculateInSampleSize(options, config.maxWidth, config.maxHeight)
        options.inJustDecodeBounds = false
        options.inPreferredConfig = Bitmap.Config.RGB_565 // Use less memory for photos
        
        val bitmap = BitmapFactory.decodeFile(inputFile.path, options) ?: return null
        
        // Apply rotation if needed
        val rotatedBitmap = applyExifRotation(bitmap, inputFile)
        
        // Resize if still too large
        return if (rotatedBitmap.width > config.maxWidth || rotatedBitmap.height > config.maxHeight) {
            val scaledBitmap = Bitmap.createScaledBitmap(
                rotatedBitmap,
                calculateNewDimensions(rotatedBitmap, config.maxWidth, config.maxHeight).first,
                calculateNewDimensions(rotatedBitmap, config.maxWidth, config.maxHeight).second,
                true
            )
            
            if (rotatedBitmap != bitmap && !rotatedBitmap.isRecycled) {
                rotatedBitmap.recycle()
            }
            
            scaledBitmap
        } else {
            rotatedBitmap
        }
    }
    
    private fun applyExifRotation(bitmap: Bitmap, file: File): Bitmap {
        return try {
            val exif = ExifInterface(file.path)
            val orientation = exif.getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)
            
            val matrix = Matrix()
            when (orientation) {
                ExifInterface.ORIENTATION_ROTATE_90 -> matrix.postRotate(90f)
                ExifInterface.ORIENTATION_ROTATE_180 -> matrix.postRotate(180f)
                ExifInterface.ORIENTATION_ROTATE_270 -> matrix.postRotate(270f)
                else -> return bitmap
            }
            
            val rotatedBitmap = Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
            
            if (rotatedBitmap != bitmap && !bitmap.isRecycled) {
                bitmap.recycle()
            }
            
            rotatedBitmap
        } catch (e: Exception) {
            logger.w(TAG, "Error applying EXIF rotation", throwable = e)
            bitmap
        }
    }
    
    private fun calculateInSampleSize(options: BitmapFactory.Options, reqWidth: Int, reqHeight: Int): Int {
        val height = options.outHeight
        val width = options.outWidth
        var inSampleSize = 1
        
        if (height > reqHeight || width > reqWidth) {
            val halfHeight = height / 2
            val halfWidth = width / 2
            
            while ((halfHeight / inSampleSize) >= reqHeight && (halfWidth / inSampleSize) >= reqWidth) {
                inSampleSize *= 2
            }
        }
        
        return inSampleSize
    }
    
    private fun calculateNewDimensions(bitmap: Bitmap, maxWidth: Int, maxHeight: Int): Pair<Int, Int> {
        val aspectRatio = bitmap.width.toFloat() / bitmap.height.toFloat()
        
        return if (bitmap.width > bitmap.height) {
            val newWidth = Math.min(maxWidth, bitmap.width)
            val newHeight = (newWidth / aspectRatio).toInt()
            newWidth to Math.min(newHeight, maxHeight)
        } else {
            val newHeight = Math.min(maxHeight, bitmap.height)
            val newWidth = (newHeight * aspectRatio).toInt()
            Math.min(newWidth, maxWidth) to newHeight
        }
    }
    
    private fun compressBitmap(bitmap: Bitmap, outputFile: File, config: ImageOptimizationConfig): Long {
        return FileOutputStream(outputFile).use { fos ->
            val success = bitmap.compress(config.format, config.quality, fos)
            fos.flush()
            
            if (!success) {
                throw IOException("Failed to compress bitmap")
            }
            
            outputFile.length()
        }
    }
    
    private fun generateThumbnail(bitmap: Bitmap, thumbnailFile: File, config: ImageOptimizationConfig) {
        val thumbBitmap = Bitmap.createScaledBitmap(bitmap, THUMBNAIL_SIZE, THUMBNAIL_SIZE, true)
        
        FileOutputStream(thumbnailFile).use { fos ->
            thumbBitmap.compress(Bitmap.CompressFormat.WEBP, WEBP_QUALITY, fos)
            fos.flush()
        }
        
        if (!thumbBitmap.isRecycled) {
            thumbBitmap.recycle()
        }
    }
    
    private fun createOptimizedFile(inputFile: File, format: Bitmap.CompressFormat): File {
        val extension = when (format) {
            Bitmap.CompressFormat.WEBP -> ".webp"
            Bitmap.CompressFormat.PNG -> ".png"
            else -> ".jpg"
        }
        
        val baseName = inputFile.nameWithoutExtension
        return File(diskCache, "${baseName}_optimized$extension")
    }
    
    private fun createThumbnailFile(inputFile: File): File {
        val baseName = inputFile.nameWithoutExtension
        return File(diskCache, "${baseName}_thumb.webp")
    }
    
    private fun generateCacheKey(file: File): String {
        return "${file.path}_${file.lastModified()}_${file.length()}"
    }
    
    private fun getDefaultConfig(): ImageOptimizationConfig {
        return when (currentOptimizationLevel) {
            OptimizationLevel.AGGRESSIVE -> ImageOptimizationConfig(
                maxWidth = 1024,
                maxHeight = 1024,
                quality = 60,
                format = Bitmap.CompressFormat.WEBP
            )
            OptimizationLevel.BALANCED -> ImageOptimizationConfig(
                maxWidth = MAX_IMAGE_DIMENSION,
                maxHeight = MAX_IMAGE_DIMENSION,
                quality = JPEG_QUALITY
            )
            OptimizationLevel.QUALITY -> ImageOptimizationConfig(
                maxWidth = 4096,
                maxHeight = 4096,
                quality = 95
            )
        }
    }
    
    /**
     * Load image from cache or optimize if not cached
     */
    suspend fun loadOptimizedImage(file: File): Bitmap? {
        return withContext(Dispatchers.IO) {
            val cacheKey = generateCacheKey(file)
            
            // Check memory cache first
            memoryCache.get(cacheKey)?.let { cachedBitmap ->
                logger.d(TAG, "Image loaded from memory cache: ${file.name}")
                return@withContext cachedBitmap
            }
            
            // Check for optimized file on disk
            val optimizedFile = File(diskCache, "${file.nameWithoutExtension}_optimized.jpg")
            val sourceFile = if (optimizedFile.exists()) optimizedFile else file
            
            try {
                val bitmap = BitmapFactory.decodeFile(sourceFile.path)
                bitmap?.let {
                    memoryCache.put(cacheKey, it)
                    logger.d(TAG, "Image loaded and cached: ${file.name}")
                }
                bitmap
            } catch (e: Exception) {
                logger.e(TAG, "Error loading image: ${file.path}", throwable = e)
                null
            }
        }
    }
    
    /**
     * Clear image caches to free memory
     */
    fun clearCaches(level: MemoryManager.MemoryLevel = MemoryManager.MemoryLevel.NORMAL) {
        when (level) {
            MemoryManager.MemoryLevel.LOW -> {
                memoryCache.trimToSize(memoryCache.size() / 2) // Reduce to half
                logger.i(TAG, "Reduced memory cache size due to low memory")
            }
            MemoryManager.MemoryLevel.CRITICAL -> {
                memoryCache.evictAll()
                compressionCache.clear()
                logger.w(TAG, "Cleared all image caches due to critical memory")
            }
            else -> {
                memoryCache.trimToSize(memoryCache.size() * 3 / 4) // Reduce to 75%
            }
        }
    }
    
    /**
     * Clean up old cached files
     */
    suspend fun cleanupDiskCache(maxAge: Long = 7 * 24 * 60 * 60 * 1000L) { // 7 days
        withContext(Dispatchers.IO) {
            try {
                val cutoffTime = System.currentTimeMillis() - maxAge
                val files = diskCache.listFiles() ?: return@withContext
                
                var deletedCount = 0
                var freedSpace = 0L
                
                files.forEach { file ->
                    if (file.lastModified() < cutoffTime) {
                        freedSpace += file.length()
                        if (file.delete()) {
                            deletedCount++
                        }
                    }
                }
                
                logger.i(TAG, "Disk cache cleanup completed", mapOf(
                    "deleted_files" to deletedCount.toString(),
                    "freed_space_mb" to (freedSpace / 1024 / 1024).toString()
                ))
                
            } catch (e: Exception) {
                logger.e(TAG, "Error during disk cache cleanup", throwable = e)
            }
        }
    }
    
    /**
     * Get cache statistics
     */
    fun getCacheStats(): Map<String, Any> {
        return mapOf(
            "memory_cache_size" to memoryCache.size(),
            "memory_cache_max_size" to memoryCache.maxSize(),
            "memory_cache_hit_count" to memoryCache.hitCount(),
            "memory_cache_miss_count" to memoryCache.missCount(),
            "compression_cache_size" to compressionCache.size,
            "disk_cache_files" to (diskCache.listFiles()?.size ?: 0),
            "disk_cache_size_mb" to calculateDiskCacheSize()
        )
    }
    
    private fun calculateDiskCacheSize(): Long {
        return try {
            val files = diskCache.listFiles() ?: return 0L
            files.sumOf { it.length() } / 1024 / 1024 // Size in MB
        } catch (e: Exception) {
            0L
        }
    }
    
    /**
     * Set optimization level based on device performance or user preference
     */
    fun setOptimizationLevel(level: OptimizationLevel) {
        currentOptimizationLevel = level
        logger.i(TAG, "Optimization level changed to: $level")
    }
    
    // MemoryManager.MemoryListener implementation
    override fun onMemoryWarning(level: MemoryManager.MemoryLevel) {
        clearCaches(level)
        
        // Adjust optimization level based on memory pressure
        when (level) {
            MemoryManager.MemoryLevel.CRITICAL -> {
                setOptimizationLevel(OptimizationLevel.AGGRESSIVE)
            }
            MemoryManager.MemoryLevel.LOW -> {
                if (currentOptimizationLevel == OptimizationLevel.QUALITY) {
                    setOptimizationLevel(OptimizationLevel.BALANCED)
                }
            }
            else -> {
                // No change for normal memory levels
            }
        }
    }
    
    override fun onMemoryOptimizationRecommended() {
        clearCaches(MemoryManager.MemoryLevel.NORMAL)
        
        optimizationScope.launch {
            cleanupDiskCache()
        }
    }
    
    fun shutdown() {
        logger.i(TAG, "Image optimizer shutting down")
        optimizationScope.cancel()
        memoryManager.removeMemoryListener(this)
        clearCaches(MemoryManager.MemoryLevel.CRITICAL)
    }
}