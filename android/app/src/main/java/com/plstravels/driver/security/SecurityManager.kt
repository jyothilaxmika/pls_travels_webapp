package com.plstravels.driver.security

import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.Build
import android.provider.Settings
import android.telephony.TelephonyManager
import com.plstravels.driver.BuildConfig
import com.scottyab.rootbeer.RootBeer
import dagger.hilt.android.qualifiers.ApplicationContext
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Comprehensive security manager for the PLS Driver app
 * Handles root detection, anti-tampering, debugger detection, and other security checks
 */
@Singleton
class SecurityManager @Inject constructor(
    @ApplicationContext private val context: Context
) {
    
    private val rootBeer = RootBeer(context)
    
    /**
     * Performs comprehensive security check
     * @return true if the device and app are secure, false otherwise
     */
    fun performSecurityCheck(): SecurityResult {
        if (!BuildConfig.SECURITY_CHECKS_ENABLED) {
            return SecurityResult(isSecure = true, threats = emptyList())
        }
        
        val threats = mutableListOf<SecurityThreat>()
        
        // Root detection
        if (isDeviceRooted()) {
            threats.add(SecurityThreat.ROOT_DETECTED)
        }
        
        // Debugger detection
        if (isDebuggerAttached()) {
            threats.add(SecurityThreat.DEBUGGER_ATTACHED)
        }
        
        // App integrity checks
        if (!isAppIntegrityValid()) {
            threats.add(SecurityThreat.APP_TAMPERED)
        }
        
        // Development tools detection
        if (isDevelopmentToolsDetected()) {
            threats.add(SecurityThreat.DEVELOPMENT_TOOLS)
        }
        
        // Emulator detection
        if (isRunningOnEmulator()) {
            threats.add(SecurityThreat.EMULATOR_DETECTED)
        }
        
        // Mock location detection
        if (isMockLocationEnabled()) {
            threats.add(SecurityThreat.MOCK_LOCATION)
        }
        
        return SecurityResult(
            isSecure = threats.isEmpty(),
            threats = threats
        )
    }
    
    /**
     * Checks if the device is rooted using multiple detection methods
     */
    private fun isDeviceRooted(): Boolean {
        return rootBeer.isRooted || 
               checkForRootBinaries() || 
               checkForRootApps() ||
               checkForDangerousProps() ||
               checkForRWPaths()
    }
    
    /**
     * Detects if a debugger is attached to the process
     */
    private fun isDebuggerAttached(): Boolean {
        return android.os.Debug.isDebuggerConnected() ||
               android.os.Debug.waitingForDebugger() ||
               isGdbServerRunning()
    }
    
    /**
     * Validates app integrity and signature using modern APIs
     */
    private fun isAppIntegrityValid(): Boolean {
        return try {
            // Check if app is debuggable (should not be in production)
            val isDebuggable = (context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
            
            // Use modern signature verification
            val isSignatureValid = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                val packageInfo = context.packageManager.getPackageInfo(
                    context.packageName,
                    PackageManager.GET_SIGNING_CERTIFICATES
                )
                validateModernAppSignature(packageInfo)
            } else {
                @Suppress("DEPRECATION")
                val packageInfo = context.packageManager.getPackageInfo(
                    context.packageName,
                    PackageManager.GET_SIGNATURES
                )
                validateAppSignature(packageInfo)
            }
            
            !isDebuggable && isSignatureValid
        } catch (e: Exception) {
            false
        }
    }
    
    /**
     * Detects development and reverse engineering tools
     */
    private fun isDevelopmentToolsDetected(): Boolean {
        val suspiciousApps = listOf(
            "com.android.development",
            "com.android.adb",
            "com.koushikdutta.vysor",
            "com.estrongs.android.pop",
            "com.speedsoftware.rootexplorer",
            "com.noshufou.android.su",
            "eu.chainfire.supersu",
            "com.zachspong.temprootremovejb",
            "com.ramdroid.appquarantine",
            "com.topjohnwu.magisk"
        )
        
        return suspiciousApps.any { isAppInstalled(it) }
    }
    
    /**
     * Enhanced emulator detection with multiple techniques
     */
    private fun isRunningOnEmulator(): Boolean {
        return isEmulatorByBuildProperties() ||
               isEmulatorByFiles() ||
               isEmulatorByNetworkOperator() ||
               isEmulatorByHardwareFeatures()
    }
    
    private fun isEmulatorByBuildProperties(): Boolean {
        return (Build.FINGERPRINT.startsWith("generic") ||
                Build.FINGERPRINT.contains("unknown") ||
                Build.FINGERPRINT.contains("test-keys") ||
                Build.MODEL.contains("google_sdk") ||
                Build.MODEL.contains("Emulator") ||
                Build.MODEL.contains("Android SDK built for") ||
                Build.MANUFACTURER.contains("Genymotion") ||
                Build.MANUFACTURER.equals("unknown", true) ||
                Build.BRAND.startsWith("generic") ||
                Build.DEVICE.startsWith("generic") ||
                "google_sdk" == Build.PRODUCT ||
                Build.HARDWARE.contains("goldfish") ||
                Build.HARDWARE.contains("ranchu") ||
                Build.BOARD.lowercase().contains("nox") ||
                Build.BOOTLOADER.lowercase().contains("nox"))
    }
    
    private fun isEmulatorByFiles(): Boolean {
        val emulatorFiles = listOf(
            "/system/lib/libc_malloc_debug_qemu.so",
            "/sys/qemu_trace",
            "/system/bin/qemu-props",
            "/dev/socket/qemud",
            "/dev/qemu_pipe",
            "/dev/socket/baseband_genyd",
            "/proc/tty/drivers"
        )
        return emulatorFiles.any { File(it).exists() }
    }
    
    private fun isEmulatorByNetworkOperator(): Boolean {
        val telephonyManager = context.getSystemService(Context.TELEPHONY_SERVICE) as? android.telephony.TelephonyManager
        return telephonyManager?.networkOperatorName?.lowercase()?.contains("android") == true
    }
    
    private fun isEmulatorByHardwareFeatures(): Boolean {
        return !context.packageManager.hasSystemFeature(android.content.pm.PackageManager.FEATURE_TELEPHONY) &&
               !context.packageManager.hasSystemFeature(android.content.pm.PackageManager.FEATURE_CAMERA)
    }
    
    /**
     * Checks if mock location is enabled using modern methods
     */
    private fun isMockLocationEnabled(): Boolean {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                // Modern way: Check for mock location apps through app ops
                val appOpsManager = context.getSystemService(Context.APP_OPS_SERVICE) as? android.app.AppOpsManager
                appOpsManager?.let {
                    val mode = it.checkOpNoThrow(
                        android.app.AppOpsManager.OPSTR_MOCK_LOCATION,
                        android.os.Process.myUid(),
                        context.packageName
                    )
                    mode == android.app.AppOpsManager.MODE_ALLOWED
                } ?: false
            } else {
                // Fallback for older versions
                @Suppress("DEPRECATION")
                val mockLocation = Settings.Secure.getString(
                    context.contentResolver,
                    Settings.Secure.ALLOW_MOCK_LOCATION
                )
                mockLocation == "1"
            }
        } catch (e: Exception) {
            false
        }
    }
    
    // Private helper methods
    
    private fun checkForRootBinaries(): Boolean {
        val rootBinaries = arrayOf(
            "/system/app/Superuser.apk",
            "/sbin/su",
            "/system/bin/su",
            "/system/xbin/su",
            "/data/local/xbin/su",
            "/data/local/bin/su",
            "/system/sd/xbin/su",
            "/system/bin/failsafe/su",
            "/data/local/su",
            "/su/bin/su"
        )
        
        return rootBinaries.any { File(it).exists() }
    }
    
    private fun checkForRootApps(): Boolean {
        val rootApps = arrayOf(
            "com.noshufou.android.su",
            "com.noshufou.android.su.elite",
            "eu.chainfire.supersu",
            "com.koushikdutta.superuser",
            "com.thirdparty.superuser",
            "com.yellowes.su",
            "com.topjohnwu.magisk",
            "com.kingroot.kinguser",
            "com.kingo.root",
            "com.smedialink.oneclickroot",
            "com.zhiqupk.root.global",
            "com.alephzain.framaroot"
        )
        
        return rootApps.any { isAppInstalled(it) }
    }
    
    private fun checkForDangerousProps(): Boolean {
        return try {
            val process = Runtime.getRuntime().exec(arrayOf("getprop", "ro.debuggable"))
            val output = process.inputStream.bufferedReader().readText().trim()
            output == "1"
        } catch (e: Exception) {
            false
        }
    }
    
    private fun checkForRWPaths(): Boolean {
        val mountReader = File("/proc/mounts")
        if (mountReader.exists()) {
            try {
                mountReader.readLines().forEach { line ->
                    val args = line.split(" ")
                    if (args.size >= 4) {
                        val mountPoint = args[1]
                        val mountOptions = args[3]
                        
                        if (mountPoint == "/system" || mountPoint == "/") {
                            if (mountOptions.contains("rw")) {
                                return true
                            }
                        }
                    }
                }
            } catch (e: Exception) {
                // Ignore
            }
        }
        return false
    }
    
    private fun isGdbServerRunning(): Boolean {
        return try {
            val process = Runtime.getRuntime().exec("ps")
            val output = process.inputStream.bufferedReader().readText()
            output.contains("gdbserver")
        } catch (e: Exception) {
            false
        }
    }
    
    private fun validateAppSignature(packageInfo: android.content.pm.PackageInfo): Boolean {
        return try {
            // For legacy API signature validation
            // In production, this should validate against a known good signature
            
            if (packageInfo.signatures.isEmpty()) {
                android.util.Log.w("SecurityManager", "Legacy signature validation failed - no signatures found")
                return false
            }
            
            // Get the first signature (primary signature)
            val signature = packageInfo.signatures[0]
            
            // For now, just verify that a signature exists and is not obviously tampered
            // In a real implementation, this would compare against a known good signature hash
            val signatureBytes = signature.toByteArray()
            
            if (signatureBytes.isEmpty()) {
                android.util.Log.w("SecurityManager", "Legacy signature validation failed - empty signature")
                return false
            }
            
            // Basic validation - signature should have reasonable size
            if (signatureBytes.size < 100) {
                android.util.Log.w("SecurityManager", "Legacy signature validation failed - signature too small")
                return false
            }
            
            // TODO: Replace with actual signature hash comparison when certificate is available
            android.util.Log.i("SecurityManager", "Legacy signature validation passed (basic checks only)")
            return true
            
        } catch (e: Exception) {
            android.util.Log.e("SecurityManager", "Legacy signature validation failed with exception", e)
            false
        }
    }
    
    private fun validateModernAppSignature(packageInfo: android.content.pm.PackageInfo): Boolean {
        return try {
            // For modern API signature validation (API 28+)
            
            val signingInfo = packageInfo.signingInfo
            if (signingInfo == null) {
                android.util.Log.w("SecurityManager", "Modern signature validation failed - no signing info")
                return false
            }
            
            val signatures = if (signingInfo.hasMultipleSigners()) {
                signingInfo.apkContentsSigners
            } else {
                signingInfo.signingCertificateHistory
            }
            
            if (signatures.isEmpty()) {
                android.util.Log.w("SecurityManager", "Modern signature validation failed - no signatures in signing info")
                return false
            }
            
            // Get the primary signature
            val signature = signatures[0]
            val signatureBytes = signature.toByteArray()
            
            if (signatureBytes.isEmpty()) {
                android.util.Log.w("SecurityManager", "Modern signature validation failed - empty signature")
                return false
            }
            
            // Basic validation - signature should have reasonable size
            if (signatureBytes.size < 100) {
                android.util.Log.w("SecurityManager", "Modern signature validation failed - signature too small")
                return false
            }
            
            // TODO: Replace with actual signature hash comparison when certificate is available
            android.util.Log.i("SecurityManager", "Modern signature validation passed (basic checks only)")
            return true
            
        } catch (e: Exception) {
            android.util.Log.e("SecurityManager", "Modern signature validation failed with exception", e)
            false
        }
    }
    
    private fun isAppInstalled(packageName: String): Boolean {
        return try {
            context.packageManager.getPackageInfo(packageName, 0)
            true
        } catch (e: PackageManager.NameNotFoundException) {
            false
        }
    }
}

/**
 * Result of security check
 */
data class SecurityResult(
    val isSecure: Boolean,
    val threats: List<SecurityThreat>
)

/**
 * Types of security threats that can be detected
 */
enum class SecurityThreat {
    ROOT_DETECTED,
    DEBUGGER_ATTACHED,
    APP_TAMPERED,
    DEVELOPMENT_TOOLS,
    EMULATOR_DETECTED,
    MOCK_LOCATION
}