package com.plstravels.driver.security

import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.Build
import com.plstravels.driver.BuildConfig
import timber.log.Timber
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Production security manager for anti-tampering and security validation
 */
@Singleton
class SecurityManager @Inject constructor(
    private val context: Context
) {
    
    companion object {
        private const val MAX_SECURITY_VIOLATIONS = 3
        private val ROOT_DETECTION_PATHS = arrayOf(
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
        
        private val ROOT_DETECTION_PACKAGES = arrayOf(
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
    }
    
    private var securityViolationCount = 0
    
    /**
     * Perform comprehensive security check
     */
    fun performSecurityCheck(): SecurityCheckResult {
        val results = mutableListOf<SecurityViolation>()
        
        try {
            // Check for debugging
            if (isDebuggingEnabled()) {
                results.add(SecurityViolation.DEBUGGING_ENABLED)
                Timber.w("Security violation: Debugging enabled")
            }
            
            // Check for root access
            if (isDeviceRooted()) {\n                results.add(SecurityViolation.ROOT_DETECTED)\n                Timber.w(\"Security violation: Root access detected\")\n            }\n            \n            // Check for emulator\n            if (isRunningOnEmulator()) {\n                results.add(SecurityViolation.EMULATOR_DETECTED)\n                Timber.w(\"Security violation: Running on emulator\")\n            }\n            \n            // Check for package tampering\n            if (isPackageTampered()) {\n                results.add(SecurityViolation.PACKAGE_TAMPERED)\n                Timber.w(\"Security violation: Package tampering detected\")\n            }\n            \n            // Check for malicious apps\n            val maliciousApps = detectMaliciousApps()\n            if (maliciousApps.isNotEmpty()) {\n                results.add(SecurityViolation.MALICIOUS_APPS_DETECTED)\n                Timber.w(\"Security violation: Malicious apps detected: $maliciousApps\")\n            }\n            \n            val criticalViolations = results.filter { it.isCritical() }\n            val severityLevel = when {\n                criticalViolations.isNotEmpty() -> SecurityLevel.CRITICAL\n                results.isNotEmpty() -> SecurityLevel.WARNING\n                else -> SecurityLevel.SECURE\n            }\n            \n            if (criticalViolations.isNotEmpty()) {\n                securityViolationCount++\n                Timber.e(\"Critical security violations detected: $criticalViolations (count: $securityViolationCount)\")\n            }\n            \n            return SecurityCheckResult(\n                isSecure = results.isEmpty(),\n                violations = results,\n                severityLevel = severityLevel,\n                shouldBlockAccess = securityViolationCount >= MAX_SECURITY_VIOLATIONS || \n                                  criticalViolations.any { it == SecurityViolation.PACKAGE_TAMPERED }\n            )\n            \n        } catch (e: Exception) {\n            Timber.e(e, \"Security check failed\")\n            return SecurityCheckResult(\n                isSecure = false,\n                violations = listOf(SecurityViolation.SECURITY_CHECK_FAILED),\n                severityLevel = SecurityLevel.CRITICAL,\n                shouldBlockAccess = true\n            )\n        }\n    }\n    \n    /**\n     * Check if debugging is enabled\n     */\n    private fun isDebuggingEnabled(): Boolean {\n        return try {\n            (context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0\n        } catch (e: Exception) {\n            Timber.e(e, \"Failed to check debugging status\")\n            false\n        }\n    }\n    \n    /**\n     * Check if device is rooted\n     */\n    private fun isDeviceRooted(): Boolean {\n        return try {\n            // Check for root files\n            val rootPathsExist = ROOT_DETECTION_PATHS.any { path ->\n                try {\n                    File(path).exists()\n                } catch (e: Exception) {\n                    false\n                }\n            }\n            \n            // Check for root packages\n            val rootPackagesInstalled = ROOT_DETECTION_PACKAGES.any { packageName ->\n                try {\n                    context.packageManager.getPackageInfo(packageName, 0)\n                    true\n                } catch (e: PackageManager.NameNotFoundException) {\n                    false\n                } catch (e: Exception) {\n                    false\n                }\n            }\n            \n            // Check for su binary access\n            val suCommandAvailable = try {\n                Runtime.getRuntime().exec(\"su\")\n                true\n            } catch (e: Exception) {\n                false\n            }\n            \n            rootPathsExist || rootPackagesInstalled || suCommandAvailable\n        } catch (e: Exception) {\n            Timber.e(e, \"Failed to check root status\")\n            false\n        }\n    }\n    \n    /**\n     * Check if running on emulator\n     */\n    private fun isRunningOnEmulator(): Boolean {\n        return try {\n            (Build.FINGERPRINT.startsWith(\"generic\") ||\n             Build.FINGERPRINT.startsWith(\"unknown\") ||\n             Build.MODEL.contains(\"google_sdk\") ||\n             Build.MODEL.contains(\"Emulator\") ||\n             Build.MODEL.contains(\"Android SDK built for x86\") ||\n             Build.MANUFACTURER.contains(\"Genymotion\") ||\n             Build.BRAND.startsWith(\"generic\") && Build.DEVICE.startsWith(\"generic\") ||\n             \"google_sdk\" == Build.PRODUCT)\n        } catch (e: Exception) {\n            Timber.e(e, \"Failed to check emulator status\")\n            false\n        }\n    }\n    \n    /**\n     * Check if package has been tampered\n     */\n    private fun isPackageTampered(): Boolean {\n        return try {\n            // In production, you would compare against a known signature hash\n            // For now, we'll check if the installer package is valid\n            val installerPackageName = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {\n                context.packageManager.getInstallSourceInfo(context.packageName).installingPackageName\n            } else {\n                @Suppress(\"DEPRECATION\")\n                context.packageManager.getInstallerPackageName(context.packageName)\n            }\n            \n            // Check if installed from a legitimate source (production check)\n            val validInstallers = listOf(\n                \"com.android.vending\", // Google Play Store\n                \"com.amazon.venezia\", // Amazon App Store\n                \"com.samsung.android.galaxyapps\", // Samsung Galaxy Store\n                null // Side-loading for development\n            )\n            \n            if (BuildConfig.DEBUG) {\n                // Allow any installer in debug builds\n                false\n            } else {\n                // In production, require valid installer\n                !validInstallers.contains(installerPackageName)\n            }\n        } catch (e: Exception) {\n            Timber.e(e, \"Failed to check package tampering\")\n            true // Assume tampered if check fails\n        }\n    }\n    \n    /**\n     * Detect malicious apps that might interfere with security\n     */\n    private fun detectMaliciousApps(): List<String> {\n        val maliciousApps = mutableListOf<String>()\n        \n        try {\n            val suspiciousPackages = listOf(\n                \"com.android.fakeapp\",\n                \"com.malware.test\",\n                \"com.chelpus.lackypatch\",\n                \"com.dimonvideo.luckypatcher\",\n                \"com.forpda.lp\",\n                \"com.android.vending.billing.InAppBillingService.COIN\",\n                \"com.android.vending.billing.InAppBillingService.LUCK\",\n                \"com.android.vending.billing.InAppBillingService.LACK\"\n            )\n            \n            val installedPackages = context.packageManager.getInstalledApplications(PackageManager.GET_META_DATA)\n            \n            for (appInfo in installedPackages) {\n                if (suspiciousPackages.contains(appInfo.packageName)) {\n                    maliciousApps.add(appInfo.packageName)\n                }\n                \n                // Check for apps with suspicious names\n                val appName = appInfo.loadLabel(context.packageManager).toString().lowercase()\n                if (appName.contains(\"hack\") || appName.contains(\"cheat\") || \n                    appName.contains(\"crack\") || appName.contains(\"patch\")) {\n                    maliciousApps.add(appInfo.packageName)\n                }\n            }\n        } catch (e: Exception) {\n            Timber.e(e, \"Failed to detect malicious apps\")\n        }\n        \n        return maliciousApps\n    }\n    \n    /**\n     * Reset security violation count (call when user successfully authenticates)\n     */\n    fun resetSecurityViolationCount() {\n        securityViolationCount = 0\n        Timber.i(\"Security violation count reset\")\n    }\n    \n    /**\n     * Get security recommendations based on violations\n     */\n    fun getSecurityRecommendations(violations: List<SecurityViolation>): List<String> {\n        val recommendations = mutableListOf<String>()\n        \n        violations.forEach { violation ->\n            when (violation) {\n                SecurityViolation.ROOT_DETECTED -> {\n                    recommendations.add(\"Remove root access from your device for enhanced security\")\n                }\n                SecurityViolation.DEBUGGING_ENABLED -> {\n                    recommendations.add(\"Install the production version of the app\")\n                }\n                SecurityViolation.EMULATOR_DETECTED -> {\n                    recommendations.add(\"Use the app on a physical device for full functionality\")\n                }\n                SecurityViolation.PACKAGE_TAMPERED -> {\n                    recommendations.add(\"Reinstall the app from the official app store\")\n                }\n                SecurityViolation.MALICIOUS_APPS_DETECTED -> {\n                    recommendations.add(\"Remove suspicious apps that may compromise security\")\n                }\n                SecurityViolation.SECURITY_CHECK_FAILED -> {\n                    recommendations.add(\"Contact support if security issues persist\")\n                }\n            }\n        }\n        \n        return recommendations\n    }\n    \n    enum class SecurityViolation {\n        ROOT_DETECTED,\n        DEBUGGING_ENABLED,\n        EMULATOR_DETECTED,\n        PACKAGE_TAMPERED,\n        MALICIOUS_APPS_DETECTED,\n        SECURITY_CHECK_FAILED;\n        \n        fun isCritical(): Boolean {\n            return when (this) {\n                ROOT_DETECTED, PACKAGE_TAMPERED, SECURITY_CHECK_FAILED -> true\n                else -> false\n            }\n        }\n    }\n    \n    enum class SecurityLevel {\n        SECURE,\n        WARNING,\n        CRITICAL\n    }\n    \n    data class SecurityCheckResult(\n        val isSecure: Boolean,\n        val violations: List<SecurityViolation>,\n        val severityLevel: SecurityLevel,\n        val shouldBlockAccess: Boolean\n    )\n}