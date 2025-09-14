package com.plstravels.driver.security

import android.content.Context
import android.content.pm.PackageManager
import android.content.pm.Signature
import java.security.MessageDigest
import java.util.zip.ZipEntry
import java.util.zip.ZipFile
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Anti-tampering detector for the PLS Driver app
 * Detects if the app has been modified, repackaged, or compromised
 */
@Singleton
class AntiTamperingDetector @Inject constructor(
    private val context: Context
) {
    
    // Expected signature hash - set to null to disable signature validation temporarily
    private val expectedSignatureHash: String? = null // Set to actual signature hash when available
    
    /**
     * Performs comprehensive anti-tampering checks
     */
    fun detectTampering(): TamperingResult {
        val issues = mutableListOf<TamperingIssue>()
        
        // Check app signature
        if (!verifyAppSignature()) {
            issues.add(TamperingIssue.INVALID_SIGNATURE)
        }
        
        // Check for repackaging
        if (isAppRepackaged()) {
            issues.add(TamperingIssue.APP_REPACKAGED)
        }
        
        // Check installer package
        if (!isInstallerValid()) {
            issues.add(TamperingIssue.INVALID_INSTALLER)
        }
        
        // Check for hooking frameworks
        if (isHookingFrameworkDetected()) {
            issues.add(TamperingIssue.HOOKING_FRAMEWORK)
        }
        
        // Check DEX file integrity
        if (!isDexIntegrityValid()) {
            issues.add(TamperingIssue.DEX_MODIFIED)
        }
        
        // Check for suspicious libraries
        if (areSuspiciousLibrariesLoaded()) {
            issues.add(TamperingIssue.SUSPICIOUS_LIBRARIES)
        }
        
        return TamperingResult(
            isTampered = issues.isNotEmpty(),
            issues = issues
        )
    }
    
    /**
     * Verifies the app's digital signature using modern API
     */
    private fun verifyAppSignature(): Boolean {
        return try {
            // If no expected signature hash is configured, skip signature validation
            // This prevents blocking legitimate users when signature hash is not yet configured
            if (expectedSignatureHash.isNullOrBlank()) {
                android.util.Log.w("AntiTamperingDetector", "Signature validation disabled - no expected hash configured")
                return true // Allow app to run, but log warning
            }
            
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.P) {
                // Use modern API for Android P (API 28) and above
                val packageInfo = context.packageManager.getPackageInfo(
                    context.packageName,
                    PackageManager.GET_SIGNING_CERTIFICATES
                )
                
                val signingInfo = packageInfo.signingInfo
                if (signingInfo == null) {
                    android.util.Log.w("AntiTamperingDetector", "Signature validation failed - no signing info")
                    return false
                }
                
                val signatures = if (signingInfo.hasMultipleSigners()) {
                    signingInfo.apkContentsSigners
                } else {
                    signingInfo.signingCertificateHistory
                }
                
                if (signatures.isEmpty()) {
                    android.util.Log.w("AntiTamperingDetector", "Signature validation failed - no signatures found")
                    return false
                }
                
                val signatureHash = getSignatureHash(signatures[0])
                val isValid = signatureHash == expectedSignatureHash
                
                if (!isValid) {
                    android.util.Log.w("AntiTamperingDetector", "Signature validation failed - hash mismatch. Expected: $expectedSignatureHash, Got: $signatureHash")
                }
                
                return isValid
            } else {
                // Fallback to legacy API for older Android versions
                @Suppress("DEPRECATION")
                val packageInfo = context.packageManager.getPackageInfo(
                    context.packageName,
                    PackageManager.GET_SIGNATURES
                )
                
                if (packageInfo.signatures.isEmpty()) {
                    android.util.Log.w("AntiTamperingDetector", "Signature validation failed - no legacy signatures found")
                    return false
                }
                
                val signature = packageInfo.signatures[0]
                val signatureHash = getSignatureHash(signature)
                val isValid = signatureHash == expectedSignatureHash
                
                if (!isValid) {
                    android.util.Log.w("AntiTamperingDetector", "Signature validation failed - legacy hash mismatch. Expected: $expectedSignatureHash, Got: $signatureHash")
                }
                
                return isValid
            }
        } catch (e: Exception) {
            android.util.Log.e("AntiTamperingDetector", "Signature validation failed with exception", e)
            false
        }
    }
    
    /**
     * Checks if the app has been repackaged
     */
    private fun isAppRepackaged(): Boolean {
        return try {
            val packageInfo = context.packageManager.getPackageInfo(context.packageName, 0)
            val sourceDir = packageInfo.applicationInfo.sourceDir
            
            // Check for META-INF modifications
            val zipFile = ZipFile(sourceDir)
            val manifestEntry = zipFile.getEntry("META-INF/MANIFEST.MF")
            val certEntry = zipFile.getEntry("META-INF/CERT.RSA") ?: zipFile.getEntry("META-INF/CERT.DSA")
            
            zipFile.close()
            
            manifestEntry == null || certEntry == null
        } catch (e: Exception) {
            true // If we can't verify, assume it's been tampered with
        }
    }
    
    /**
     * Validates the installer package (should be Google Play Store in production)
     */
    private fun isInstallerValid(): Boolean {
        val validInstallers = setOf(
            "com.android.vending", // Google Play Store
            "com.google.android.packageinstaller", // Google Package Installer
            "com.android.packageinstaller", // System Package Installer
            null // Direct installation (for debug builds)
        )
        
        val installer = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.R) {
            context.packageManager.getInstallSourceInfo(context.packageName).installingPackageName
        } else {
            @Suppress("DEPRECATION")
            context.packageManager.getInstallerPackageName(context.packageName)
        }
        return validInstallers.contains(installer)
    }
    
    /**
     * Detects hooking frameworks like Xposed, Frida, etc.
     */
    private fun isHookingFrameworkDetected(): Boolean {
        val hookingFrameworks = listOf(
            "de.robv.android.xposed.XposedBridge",
            "com.android.internal.os.ZygoteInit",
            "com.saurik.substrate",
            "com.criticalblue.android.AppProtector"
        )
        
        return hookingFrameworks.any { framework ->
            try {
                Class.forName(framework)
                true
            } catch (e: ClassNotFoundException) {
                false
            }
        } || isNativeHookingDetected()
    }
    
    /**
     * Checks DEX file integrity
     */
    private fun isDexIntegrityValid(): Boolean {
        return try {
            val packageInfo = context.packageManager.getPackageInfo(context.packageName, 0)
            val sourceDir = packageInfo.applicationInfo.sourceDir
            
            val zipFile = ZipFile(sourceDir)
            val dexEntry = zipFile.getEntry("classes.dex")
            
            if (dexEntry == null) {
                zipFile.close()
                return false
            }
            
            // Check DEX file size and basic structure
            val inputStream = zipFile.getInputStream(dexEntry)
            val dexBytes = inputStream.readBytes()
            inputStream.close()
            zipFile.close()
            
            // Basic DEX magic number check
            dexBytes.size > 8 && 
            dexBytes[0] == 0x64.toByte() && // 'd'
            dexBytes[1] == 0x65.toByte() && // 'e'
            dexBytes[2] == 0x78.toByte()    // 'x'
        } catch (e: Exception) {
            false
        }
    }
    
    /**
     * Checks for suspicious native libraries
     */
    private fun areSuspiciousLibrariesLoaded(): Boolean {
        val suspiciousLibs = listOf(
            "libfridagadget.so",
            "libfrida-agent.so",
            "libxposed_art.so",
            "libsubstrate.so",
            "libsubstrate-dvm.so"
        )
        
        return try {
            val mapsFile = java.io.File("/proc/self/maps")
            if (mapsFile.exists()) {
                val mapsContent = mapsFile.readText()
                suspiciousLibs.any { lib -> mapsContent.contains(lib) }
            } else {
                false
            }
        } catch (e: Exception) {
            false
        }
    }
    
    /**
     * Detects native hooking
     */
    private fun isNativeHookingDetected(): Boolean {
        return try {
            // Check for common native hooking indicators
            val statusFile = java.io.File("/proc/self/status")
            if (statusFile.exists()) {
                val status = statusFile.readText()
                status.contains("TracerPid:\t") && !status.contains("TracerPid:\t0")
            } else {
                false
            }
        } catch (e: Exception) {
            false
        }
    }
    
    /**
     * Generates hash of the app signature
     */
    private fun getSignatureHash(signature: Signature): String {
        val md = MessageDigest.getInstance("SHA-256")
        md.update(signature.toByteArray())
        return bytesToHex(md.digest())
    }
    
    /**
     * Converts byte array to hex string
     */
    private fun bytesToHex(bytes: ByteArray): String {
        val hexChars = "0123456789ABCDEF"
        val result = StringBuilder(bytes.size * 2)
        
        bytes.forEach { byte ->
            val i = byte.toInt() and 0xFF
            result.append(hexChars[i ushr 4])
            result.append(hexChars[i and 0x0F])
        }
        
        return result.toString()
    }
}

/**
 * Result of tampering detection
 */
data class TamperingResult(
    val isTampered: Boolean,
    val issues: List<TamperingIssue>
)

/**
 * Types of tampering issues that can be detected
 */
enum class TamperingIssue {
    INVALID_SIGNATURE,
    APP_REPACKAGED,
    INVALID_INSTALLER,
    HOOKING_FRAMEWORK,
    DEX_MODIFIED,
    SUSPICIOUS_LIBRARIES
}