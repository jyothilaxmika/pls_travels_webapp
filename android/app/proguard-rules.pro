# ================================================================================================
# PLS Driver App - Comprehensive ProGuard Rules
# ================================================================================================

# ================================================================================================
# BASIC ANDROID CONFIGURATION
# ================================================================================================

# Keep native methods
-keepclasseswithmembernames class * {
    native <methods>;
}

# Keep enums
-keepclassmembers enum * {
    public static **[] values();
    public static ** valueOf(java.lang.String);
}

# Keep Parcelable implementations
-keepclassmembers class * implements android.os.Parcelable {
    public static final ** CREATOR;
}

# Keep serializable classes
-keepclassmembers class * implements java.io.Serializable {
    static final long serialVersionUID;
    private static final java.io.ObjectStreamField[] serialPersistentFields;
    private void writeObject(java.io.ObjectOutputStream);
    private void readObject(java.io.ObjectInputStream);
    java.lang.Object writeReplace();
    java.lang.Object readResolve();
}

# ================================================================================================
# ANDROIDX & ANDROID JETPACK
# ================================================================================================

# AndroidX Rules
-keep class androidx.** { *; }
-keep interface androidx.** { *; }
-dontwarn androidx.**

# Compose Rules
-keep class androidx.compose.** { *; }
-keep interface androidx.compose.** { *; }
-dontwarn androidx.compose.**

# Navigation Component
-keep class androidx.navigation.** { *; }
-keepclassmembers class androidx.navigation.** { *; }

# Room Database
-keep class androidx.room.** { *; }
-keep interface androidx.room.** { *; }
-dontwarn androidx.room.**

# Work Manager
-keep class androidx.work.** { *; }
-keep interface androidx.work.** { *; }
-dontwarn androidx.work.**

# ================================================================================================
# SECURITY LIBRARIES
# ================================================================================================

# Root detection library
-keep class com.scottyab.rootbeer.** { *; }
-dontwarn com.scottyab.rootbeer.**

# TrustKit Certificate Pinning
-keep class com.datatheorem.android.trustkit.** { *; }
-dontwarn com.datatheorem.android.trustkit.**

# SQLCipher
-keep class net.zetetic.database.** { *; }
-keep class net.zetetic.database.sqlcipher.** { *; }
-dontwarn net.zetetic.database.**

# Security Crypto
-keep class androidx.security.crypto.** { *; }
-dontwarn androidx.security.crypto.**

# DexGuard Runtime
-keep class com.guardsquare.** { *; }
-dontwarn com.guardsquare.**

# Conscrypt
-keep class org.conscrypt.** { *; }
-dontwarn org.conscrypt.**

# ================================================================================================
# NETWORKING & HTTP
# ================================================================================================

# Retrofit
-keepattributes Signature, InnerClasses, EnclosingMethod
-keepattributes RuntimeVisibleAnnotations, RuntimeVisibleParameterAnnotations
-keepattributes AnnotationDefault
-keepclassmembers,allowshrinking,allowobfuscation interface * {
    @retrofit2.http.* <methods>;
}
-dontwarn okio.**
-dontwarn javax.annotation.**
-dontwarn retrofit2.Platform$Java8

# OkHttp
-keep class okhttp3.** { *; }
-keep interface okhttp3.** { *; }
-dontwarn okhttp3.**
-dontwarn okio.**

# ================================================================================================
# DEPENDENCY INJECTION - HILT/DAGGER
# ================================================================================================

# Hilt
-keep class dagger.hilt.** { *; }
-keep class * extends dagger.hilt.** { *; }
-keep @dagger.hilt.InstallIn class *
-keep @dagger.hilt.android.AndroidEntryPoint class * {
    <init>(...);
}
-keepclasseswithmembers class * {
    @dagger.hilt.android.AndroidEntryPoint <methods>;
}

# Dagger
-dontwarn com.google.errorprone.annotations.**
-keepclassmembers class * {
    @javax.inject.* *;
    @dagger.* *;
    <init>();
}

# ================================================================================================
# GOOGLE PLAY SERVICES & FIREBASE
# ================================================================================================

# Play Services
-keep class com.google.android.gms.** { *; }
-dontwarn com.google.android.gms.**

# Firebase
-keep class com.google.firebase.** { *; }
-dontwarn com.google.firebase.**

# Safety Net
-keep class com.google.android.gms.safetynet.** { *; }
-dontwarn com.google.android.gms.safetynet.**

# ================================================================================================
# JSON PROCESSING
# ================================================================================================

# Gson
-keepattributes Signature
-keepattributes *Annotation*
-dontwarn sun.misc.**
-keep class com.google.gson.** { *; }
-keep class * implements com.google.gson.TypeAdapterFactory
-keep class * implements com.google.gson.JsonSerializer
-keep class * implements com.google.gson.JsonDeserializer

# Jackson
-keep class com.fasterxml.jackson.** { *; }
-dontwarn com.fasterxml.jackson.**

# ================================================================================================
# KOTLIN & COROUTINES
# ================================================================================================

# Kotlin
-keep class kotlin.** { *; }
-keep class kotlin.Metadata { *; }
-dontwarn kotlin.**
-keepclassmembers class **$WhenMappings {
    <fields>;
}

# Kotlin Coroutines
-keep class kotlinx.coroutines.** { *; }
-dontwarn kotlinx.coroutines.**

# ================================================================================================
# APPLICATION-SPECIFIC RULES
# ================================================================================================

# Keep all model classes (data classes)
-keep class com.plstravels.driver.data.models.** { *; }

# Keep API interfaces
-keep interface com.plstravels.driver.data.network.** { *; }

# Keep Repository classes
-keep class com.plstravels.driver.data.repository.** { *; }

# Keep ViewModel classes
-keep class **ViewModel { *; }
-keep class * extends androidx.lifecycle.ViewModel { *; }

# Keep Service classes
-keep class com.plstravels.driver.service.** { *; }

# Keep Worker classes
-keep class com.plstravels.driver.workers.** { *; }

# Keep Utils classes that might be called via reflection
-keep class com.plstravels.driver.utils.** { *; }

# ================================================================================================
# SECURITY HARDENING RULES
# ================================================================================================

# Obfuscate security-sensitive method names
-keepclassmembers class com.plstravels.driver.utils.SecurityUtils {
    # Keep only public interface, obfuscate implementation
    public *;
}

# Remove logging in production
-assumenosideeffects class android.util.Log {
    public static boolean isLoggable(java.lang.String, int);
    public static int v(...);
    public static int i(...);
    public static int w(...);
    public static int d(...);
    public static int e(...);
}

# Remove debug-specific code
-assumenosideeffects class kotlin.jvm.internal.Intrinsics {
    static void checkParameterIsNotNull(java.lang.Object, java.lang.String);
}

# ================================================================================================
# OPTIMIZATION SETTINGS
# ================================================================================================

# Enable aggressive optimizations
-optimizations !code/simplification/arithmetic,!code/simplification/cast,!field/*,!class/merging/*
-optimizationpasses 5
-allowaccessmodification
-mergeinterfacesaggressively

# Reduce APK size
-repackageclasses ''
-keepattributes SourceFile,LineNumberTable

# ================================================================================================
# ANTI-REVERSE ENGINEERING
# ================================================================================================

# Rename classes and packages
-flattenpackagehierarchy
-repackageclasses ''

# Remove unused code and resources
-dontshrink
-dontoptimize

# String encryption (if using advanced obfuscation tools)
-keep class **.R
-keep class **.R$* {
    <fields>;
}

# ================================================================================================
# TESTING RULES (DEBUG BUILDS)
# ================================================================================================

# Keep test-related classes only in debug builds
-keep class androidx.test.** { *; }
-keep class org.junit.** { *; }
-keep class org.mockito.** { *; }
-dontwarn androidx.test.**
-dontwarn org.junit.**
-dontwarn org.mockito.**

# ================================================================================================
# CAMERA & MEDIA
# ================================================================================================

# Camera X
-keep class androidx.camera.** { *; }
-dontwarn androidx.camera.**

# ExifInterface
-keep class androidx.exifinterface.** { *; }
-dontwarn androidx.exifinterface.**

# ================================================================================================
# SUPPRESSED WARNINGS
# ================================================================================================

# Suppress warnings for known safe issues
-dontwarn java.lang.invoke.**
-dontwarn java.lang.management.**
-dontwarn javax.crypto.**
-dontwarn sun.security.**
-dontwarn java.beans.**
-dontwarn javax.naming.**