# ================================================================================================
# PLS Driver App - Staging ProGuard Rules
# ================================================================================================

# ================================================================================================
# STAGING-SPECIFIC CONFIGURATION
# ================================================================================================

# Keep logging for debugging in staging
-keep class com.jakewharton.timber.** { *; }
-dontwarn com.jakewharton.timber.**

# Keep Flipper for debugging
-keep class com.facebook.flipper.** { *; }
-dontwarn com.facebook.flipper.**

# Allow some debugging capabilities
-dontobfuscate class com.plstravels.driver.utils.DebugUtils
-keep class com.plstravels.driver.utils.DebugUtils { *; }

# Keep detailed stack traces for better debugging
-keepattributes SourceFile,LineNumberTable
-keepattributes LocalVariableTable,LocalVariableTypeTable

# ================================================================================================
# SECURITY RULES FOR STAGING
# ================================================================================================

# Enable basic security checks but allow debugging
-keep class com.plstravels.driver.security.** { 
    public *;
}

# Keep some logging for security events
-assumenosideeffects class android.util.Log {
    public static int v(...);
    public static int d(...);
}

# ================================================================================================
# STAGING BUILD OPTIMIZATIONS
# ================================================================================================

# Moderate optimization for staging
-optimizationpasses 3
-optimizations !code/simplification/arithmetic,!field/*,!class/merging/*

# Keep class names for better crash reports
-keepnames class ** { *; }

# ================================================================================================
# STAGING NETWORK CONFIGURATION
# ================================================================================================

# Allow debugging of network requests in staging
-keep class okhttp3.logging.** { *; }
-dontwarn okhttp3.logging.**

# Keep network interceptors for debugging
-keep class com.plstravels.driver.network.**Interceptor { *; }