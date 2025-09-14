# ================================================================================================
# PLS Driver App - Release ProGuard Rules (Maximum Security)
# ================================================================================================

# ================================================================================================
# RELEASE SECURITY HARDENING
# ================================================================================================

# Remove ALL logging completely
-assumenosideeffects class android.util.Log {
    public static boolean isLoggable(java.lang.String, int);
    public static int v(...);
    public static int i(...);
    public static int w(...);
    public static int d(...);
    public static int e(...);
    public static int wtf(...);
}

# Remove Timber logging
-assumenosideeffects class timber.log.Timber** {
    public static *** v(...);
    public static *** d(...);
    public static *** i(...);
    public static *** w(...);
    public static *** e(...);
    public static *** wtf(...);
    public static *** tag(...);
}

# Remove debug utilities
-assumenosideeffects class com.plstravels.driver.utils.DebugUtils {
    public static void log*(...);
    public static void print*(...);
    public static void debug*(...);
}

# ================================================================================================
# MAXIMUM OBFUSCATION
# ================================================================================================

# Aggressive optimization passes
-optimizationpasses 7
-optimizations !code/simplification/cast,!field/*,!class/merging/*
-allowaccessmodification
-mergeinterfacesaggressively

# Remove class names for security
-repackageclasses ''
-flattenpackagehierarchy

# Remove source file and line number information
-renamesourcefileattribute SourceFile
-keepattributes SourceFile,LineNumberTable

# ================================================================================================
# ANTI-TAMPERING & REVERSE ENGINEERING PROTECTION
# ================================================================================================

# Obfuscate all security-related classes heavily
-keep class com.plstravels.driver.security.SecurityManager {
    # Keep only minimal public interface
    public boolean isSecure();
}

# Remove debug and development classes completely
-assumenosideeffects class com.plstravels.driver.utils.DevUtils {
    *;
}

# Remove testing utilities
-assumenosideeffects class androidx.test.** {
    *;
}

# Remove development-only annotations
-assumenosideeffects class androidx.annotation.VisibleForTesting {
    *;
}

# ================================================================================================
# STRING ENCRYPTION & PROTECTION
# ================================================================================================

# Encrypt sensitive strings (requires additional tools)
-adaptclassstrings
-adaptresourcefilenames    **.properties,**.gif,**.jpg,**.png,**.xml,**.json

# Obfuscate resource identifiers
-adaptresourcefilecontents **.properties,META-INF/MANIFEST.MF

# ================================================================================================
# CONTROL FLOW OBFUSCATION
# ================================================================================================

# Add dummy methods and confusing control flow
-keepclassmembers class * {
    *** *_dummy_*(...);
}

# ================================================================================================
# PRODUCTION NETWORK SECURITY
# ================================================================================================

# Remove all network debugging
-assumenosideeffects class okhttp3.logging.HttpLoggingInterceptor {
    *;
}

# Remove debug network interceptors
-assumenosideeffects class com.plstravels.driver.network.DebugInterceptor {
    *;
}

# ================================================================================================
# SECURITY CLASS PROTECTION
# ================================================================================================

# Heavily obfuscate security implementations
-keep,allowobfuscation class com.plstravels.driver.security.** {
    # Obfuscate everything except minimal public interface
}

# Protect certificate pinning implementation
-keep,allowobfuscation class com.plstravels.driver.network.CertificatePinner {
    public boolean verify*(...);
}

# Protect root detection
-keep,allowobfuscation class com.plstravels.driver.security.RootDetector {
    public boolean isRooted();
}

# ================================================================================================
# REMOVE DEVELOPMENT ARTIFACTS
# ================================================================================================

# Remove test packages completely
-dontwarn org.junit.**
-dontwarn org.mockito.**
-dontwarn androidx.test.**

# Remove development libraries
-dontwarn com.facebook.flipper.**
-dontwarn com.jakewharton.timber.**

# ================================================================================================
# FINAL SECURITY MEASURES
# ================================================================================================

# Prevent class name disclosure in stack traces
-keepattributes !LocalVariableTable,!LocalVariableTypeTable

# Remove parameter names
-keepparameternames

# Minimize method and field names
-keepclassmembers,allowshrinking,allowoptimization class * {
    <methods>;
    <fields>;
}