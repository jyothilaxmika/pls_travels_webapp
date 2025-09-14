package com.plstravels.driver.di

import com.plstravels.driver.BuildConfig
import com.plstravels.driver.data.network.ApiService
import com.plstravels.driver.data.network.AuthInterceptor
import com.plstravels.driver.data.network.RefreshApiService
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Named
import okhttp3.CertificatePinner
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

/**
 * Hilt module for network dependencies
 */
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {
    
    @Provides
    @Singleton
    fun provideCertificatePinner(): CertificatePinner? {
        // Only enable certificate pinning in release builds with actual pins configured
        if (BuildConfig.DEBUG) {
            // Never use certificate pinning in debug builds for development flexibility
            return null
        }
        
        // Define expected certificate pins - these should be replaced with actual values
        val productionPins = mapOf(
            "api.plstravels.com" to listOf(
                "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=", // Placeholder - replace with actual pin
                "sha256/BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB="  // Backup pin
            ),
            "staging-api.plstravels.com" to listOf(
                "sha256/CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC=", // Placeholder - replace with actual pin
                "sha256/DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD="  // Backup pin
            )
        )
        
        // Check if pins are still placeholders (all A's, B's, etc.)
        val hasPlaceholderPins = productionPins.values.flatten().any { pin ->
            pin.contains("AAAAAAAA") || pin.contains("BBBBBBBB") || 
            pin.contains("CCCCCCCC") || pin.contains("DDDDDDDD")
        }
        
        if (hasPlaceholderPins) {
            // In production, if pins are still placeholders, don't enable pinning
            // Log warning in production builds (this would need a logger)
            android.util.Log.w("NetworkModule", "Certificate pinning disabled - placeholder pins detected")
            return null
        }
        
        // Build certificate pinner with actual pins
        val builder = CertificatePinner.Builder()
        productionPins.forEach { (hostname, pins) ->
            pins.forEach { pin ->
                builder.add(hostname, pin)
            }
        }
        
        return builder.build()
    }

    @Provides
    @Singleton
    @Named("base")
    fun provideBaseOkHttpClient(certificatePinner: CertificatePinner?): OkHttpClient {
        val builder = OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
        
        // Apply certificate pinning only if available and not in debug builds
        if (!BuildConfig.DEBUG && certificatePinner != null) {
            builder.certificatePinner(certificatePinner)
        }
        
        // Add logging only in debug builds
        if (BuildConfig.DEBUG) {
            val loggingInterceptor = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            }
            builder.addInterceptor(loggingInterceptor)
        }
        
        return builder.build()
    }
    
    @Provides
    @Singleton
    @Named("auth")
    fun provideAuthOkHttpClient(@Named("base") baseOkHttpClient: OkHttpClient, authInterceptor: AuthInterceptor): OkHttpClient {
        return baseOkHttpClient.newBuilder()
            .addInterceptor(authInterceptor)
            .build()
    }
    
    @Provides
    @Singleton
    @Named("auth")
    fun provideAuthRetrofit(@Named("auth") okHttpClient: OkHttpClient): Retrofit {
        return Retrofit.Builder()
            .baseUrl(BuildConfig.API_BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }
    
    @Provides
    @Singleton
    @Named("refresh")
    fun provideRefreshRetrofit(@Named("base") okHttpClient: OkHttpClient): Retrofit {
        return Retrofit.Builder()
            .baseUrl(BuildConfig.API_BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }
    
    @Provides
    @Singleton
    fun provideApiService(@Named("auth") retrofit: Retrofit): ApiService {
        return retrofit.create(ApiService::class.java)
    }
    
    @Provides
    @Singleton
    fun provideRefreshApiService(@Named("refresh") retrofit: Retrofit): RefreshApiService {
        return retrofit.create(RefreshApiService::class.java)
    }
}